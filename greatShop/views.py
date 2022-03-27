from django.shortcuts import render
from store.models import Product,ReviewRating

#recommendation libraries
import pandas as pd
from surprise import Reader
from surprise import SVD
from surprise.model_selection import cross_validate
from surprise import Dataset
from surprise import accuracy
from surprise.model_selection import train_test_split


def home(request):

    section_recommendation =True
    products=[]
    products_recommended=[]
    if request.user.is_authenticated:
        rating = ReviewRating.objects.values_list('rating',flat=True) 
        userID = ReviewRating.objects.values_list('user_id', flat=True)
        itemID = ReviewRating.objects.values_list('product_id', flat=True) 

        df=pd.DataFrame(list(zip(userID, itemID,rating)),
        columns =['userID', 'itemID', 'rating'])
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(df[['userID', 'itemID', 'rating']], reader)
        svd = SVD(verbose=True, n_epochs=20)
        cross_validate(svd, data, measures=['RMSE', 'MAE'], cv=3, verbose=True)
        trainset, testset = train_test_split(data, test_size=.25)
        # We'll use the famous SVD algorithm.
        # Train the algorithm on the trainset, and predict ratings for the testset
        svd.fit(trainset) 
        predictions = svd.test(testset)

        database_products = Product.objects.all()
        
        for product in database_products:
            rating_item = svd.predict(uid=request.user.id, iid=product.id)
            if(rating_item.est >4.5):
                products_recommended.append(product)
    else:
        section_recommendation = False
    
       
    products = Product.objects.filter(is_popular=True)


    
    #generate_product_list_features()
    context = {

        'products_recommended': products_recommended,
        'products' : products,
        'section_recommendation' : section_recommendation,
    
            }
    return render(request, 'home.html', context)