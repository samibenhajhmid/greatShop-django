from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating
from category.models import Category
from carts.models import CartItem
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import  Paginator
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct
#importing requiered bibiotheque
from rake_nltk import Rake
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel   
#start_time = datetime.now()

#print("--- %s seconds ---" % (datetime.now() - start_time))


def get_categories_correlation(sub_category1, sub_category2):
    correlation=0
    cat_level_1=sub_category1[0:sub_category1.find('/')]
    index=sub_category1.find('/')
    index_1 = sub_category1.find('/', index+1,len(sub_category1))
    #index_2 = sub_category1.find('/', index_1+1,len(sub_category1))
    cat_level_2=sub_category1[0:index_1]
    cat_level_3 = sub_category1[0:len(cat_level_2)+5]
    if(sub_category2.find(cat_level_1)>=0):
        correlation=correlation+3
    if(sub_category2.find(cat_level_2)>=0):
        correlation=correlation+3
    if(sub_category2.find(cat_level_3)>=0):
        correlation=correlation+3
    return correlation

def get_description_correlation_tf_idf(text1, text2):

    #nltk.download('punkt') # if necessary...
    search_terms = text1
    documents = [text2]

    doc_vectors = TfidfVectorizer().fit_transform([search_terms] + documents)

    cosine_similarities = linear_kernel(doc_vectors[0:1], doc_vectors).flatten()
    document_scores = [item.item() for item in cosine_similarities[1:]]
    return round((document_scores[0]*3))





def get_tiltle_simularity_degree(phrase1, phrase2):   
    title_correlation=0 
    r_phrase1=Rake()
    r_phrase2=Rake()
    r_phrase1.extract_keywords_from_text(phrase1)
    r_phrase2.extract_keywords_from_text(phrase2)
    list_phrase1=r_phrase1.get_ranked_phrases()
    list_phrase2=r_phrase2.get_ranked_phrases()    
    list_phrase2_split =[]
    for j in list_phrase2:
         for k in (j.split()):
             list_phrase2_split.append(k)
    for item in list_phrase1:
        for i in item.split():
             if(i in list_phrase2_split):
                title_correlation=title_correlation+1 
              
    return title_correlation

def get_simular_products(product_id):
    current_product = Product.objects.get(id=product_id)
    products= Product.objects.values_list('id', 'product_name', 'description', 'product_brand', 'sub_category','is_popular')
    simularity_degree=[]
    simularity_brand=0
    simularity_category=0
    degree=0
    simularity_description=0
    simularity_title=0
    simularity_dict={}

    for product in products:
        if(product[3] == current_product.product_brand):
            simularity_brand=3
        simularity_category=get_categories_correlation (product[4],current_product.sub_category)              
        simularity_description=get_description_correlation_tf_idf(product[2],current_product.description)
        simularity_title = get_tiltle_simularity_degree(product[1],current_product.product_name)
        degree=simularity_brand+simularity_category+simularity_title+simularity_description
        if(degree>6):
            simularity_dict[product[0]]=degree
            top_recommended_products=sorted(simularity_dict, key=simularity_dict.get, reverse=True)[:10]
    return top_recommended_products


    #return(simularity_degree)


def store(request, category_slug=None):
    categories = None
    products = None

    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        paginator = Paginator(products, 30)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')
        paginator = Paginator(products, 30)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None

    # Get the reviews
    simular_products_to_display=[]
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)
    #current_product = Product.objects.get(slug=single_product.slug)
    #current_product_to_use = current_product[0]
    if( not single_product.related_products):
        simular_products=get_simular_products(single_product.id)
        single_product.related_products=simular_products
        single_product.save()
    else:
        for ids in single_product.related_products:
            if(ids!=single_product.id):
                simular_products_to_display.append(Product.objects.get(id=int(ids)))

        
    context = {
        'simular_products_to_display' : simular_products_to_display,
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        #'top_recommended_products':top_recommended_products,
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated.')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)

