from celery import shared_task
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.conf import settings
import os
import numpy as np
from .utils import _pairwise_distances, process_img_batch, init_model
import shutil
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
from io import StringIO, BytesIO
from time import sleep
from .models import LostPost, FoundPost, CandidateMatch
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '3'
from django.utils import timezone
import tensorflow as tf
from django.core.cache import cache
import time
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from authy.models import Cat

# receive a user_id and a list of foundpost_id
def sendEmailtoUser(lostpost_id,foundpost_ids):

    posts = FoundPost.objects.filter(id__in=foundpost_ids)  # Get your posts
    subject = 'We found a match for your Lost Post in Petnet! Check right away'
    from_email = settings.EMAIL_HOST_USER
    recipient_list =   LostPost.objects.get(id=lostpost_id).email# List of recipients 

    html_content = render_to_string('email_template.html', {'posts': posts})
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.send()

@shared_task()
def createEmbeddingCat(cat_id):
    cat = Cat.objects.get(id=cat_id)
    image_fol = cat.img_fol()
    filepaths = [os.path.join(image_fol,filename) for filename in os.listdir(image_fol)]
    model_fol = os.path.join(settings.BASE_DIR,'resnet')
    model_path= os.path.join(model_fol,'resnet_50v2_emb_32_margin_02_alpha_05_60_epoch.h5')
    model = init_model()
    model.load_weights(model_path)

    cat_emb = process_img_batch(filepaths,model)
    dist_cat= _pairwise_distances(cat_emb, squared=False)[0]
    mean_emb=np.mean(dist_cat,axis=0)
    ind=np.argsort(mean_emb)

    # SAVE 3 EMBEDDING VECTORs THAT HAS THE BEST REPRESENTATIVE POWER
    data=cat_emb[ind[:3]] # of shape (3,32)
    data=np.asarray(data)

    # SAVE TO embedding
    buffer = BytesIO()
    np.save(buffer, data)
    buffer.seek(0)

    # Create a Django ContentFile
    file = ContentFile(buffer.getvalue())

    # Generate a filename (you might want to make this more sophisticated)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{cat_id}_{timestamp}.npy"

    # Save the file to the model's file field in byte format
    getattr(cat, 'embedding_vector').save(filename, file, save=False)
    # save to the cat instance
    cat.save()
    
    # notify for user

    # notify= Notification.objects.create(
    #             cat=cat,
    #             user=cat.user,
    #             notification_type=6
    #         )
    
    # channel_layer = get_channel_layer()
    # async_to_sync(channel_layer.group_send)(
    #     f"user_{cat.user.id}",
    #     {"type":"send_notification",
    #      "message":{
    #          "action":"embedding_completed",
    #      }}
    # )




@shared_task()
def createEmbedding(post_id,found=False,field_name="embedding"):
    """
    Usage: Given a post (lost or found), create an embedding vector that represent the images

    After being created, embedding is saved to 'media/embeddings/
    """
    if found:
        post = FoundPost.objects.get(id=post_id)
    else:
        post = LostPost.objects.get(id=post_id)
    
    model_fol = os.path.join(settings.BASE_DIR,'resnet')
    model_path= os.path.join(model_fol,'resnet_50v2_emb_32_margin_02_alpha_05_60_epoch.h5')
    model = init_model()
    model.load_weights(model_path)
        
    # img_dir=os.path.normpath(img_dir)
    filepaths = list()
    for file in post.content.all():

        filepath = file.file.path
        filepaths.append(filepath)

    cat_emb=process_img_batch(filepaths,model)
    if len(filepaths)>=3:
    
        dist_cat= _pairwise_distances(cat_emb, squared=False)[0]
        mean_emb=np.mean(dist_cat,axis=0)
        ind=np.argsort(mean_emb)

        # SAVE ONE EMBEDDING VECTOR THAT HAS THE BEST REPRESENTATIVE POWER
        data=cat_emb[ind[:3]] # of shape (3,32)
        data=np.asarray(data)

    buffer = BytesIO()
    np.save(buffer, data)
    buffer.seek(0)

        # Create a Django ContentFile
    file = ContentFile(buffer.getvalue())

    # Generate a filename (you might want to make this more sophisticated)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{post_id}_{timestamp}.npy"

    # Save the file to the model's file field in byte format
    getattr(post, field_name).save(filename, file, save=False)

    # Save the model instance
    post.save()
    if found:

        notify= Notification.objects.create(
                    post=post,
                    user=post.user,
                    notification_type=5
                )
    else:
        notify= Notification.objects.create(
            post=post,
            user=post.user,
            notification_type=4
        )

        
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{post.user.id}",
        {"type":"send_notification",
         "message":{
             "action":"embedding_completed",
         }}
    )
    

import numpy as np
import pandas as pd
import ast


def load_embeddings(csv_file_path):
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path)
    
    # Initialize a list to hold the embedding vectors
    embeddings = []
    
    # Iterate through the DataFrame rows
    for embedding_str in df['embedding']:
        # Convert the string representation of the numpy array back to an actual numpy array
        embedding = np.array(ast.literal_eval(embedding_str))
        embeddings.append(embedding)
    
    # Stack all embedding vectors into a single numpy matrix
    embeddings_matrix = np.vstack(embeddings)
    ids = df['id'].to_numpy()
    return ids,embeddings_matrix

def read_file(filepath):
    """
    Read a file in byte to return array
    """
    with open(filepath,'rb') as f:
        return np.load(f)
    
def test_result(filename,result):
    #result is an embedding vector of shape (1,32)
    # anchors is 
    # return False if 2 out of 3 vector return result>0.5
    anchors= read_file(filename)
    dist=anchors-result
    dist=np.square(dist)
    dist=np.sum(dist,axis=1)
    dist=np.sqrt(dist)
    dist_05=np.less(dist,0.5)
    dist_06=np.less(dist,0.6)
    if np.sum(dist_06)>=2 or np.sum(dist_05)>=1:
        return True
    else:
        return False

@shared_task()
def matchCat(post_id,in_batch=False):
    """
    1.given an embedding vector, search for a match
    2. We store all embedding vector of found cat into a file if in_batch=True
    This is a feature that has not been implemented yet

    """
    post = LostPost.objects.get(id=post_id)
    lost = read_file(post.embedding.path) # of shape (3,32)
    B = np.expand_dims(lost,axis=0) # of shape (1,3,32)

    if in_batch:
    # embedding of shape (n,32)
        ids, embeddings = load_embeddings('media/found_embeddings.csv')
    else:
        founds = FoundPost.objects.all()
        ids = []
        embeddings = []
        for found in founds:
            id = found.id
            embedding = read_file(found.embedding.path)
            ids.append(id)
            embeddings.append(embedding)
        A = np.stack(embeddings,axis=0) # of shape (m,3,32)
        print(A.shape)

        m = A.shape[0]
        print(m)
        ids = np.array(ids)
    
    # compute matrix C of shape (m,3,3) that C[i][j][k] is
    """
    C[i][j][k] is the euclidean distance between 
    A[i][j] and B[0][k]
    """
    # B_exp = B[:, :, np.newaxis, :]  # shape (1, 3, 1, 32)
    # print('CHECK 1:',B_exp.shape)

    # Step 2: Compute the differences
    # A: shape (m, 3, 32) -> (m, 3, 1, 32)

    A_reshaped = A[:, :, np.newaxis, :] 
    squared_diff = (A_reshaped - B) ** 2
    C = np.sqrt(np.sum(squared_diff, axis=-1)) # of shape (m,3,3)

    print('CHECK 2',C.shape)


    # turn C into (m,9)

    C = np.reshape(C,(m,9)) 

    min_matrix = np.min(C,axis=1) # of shape (m,)

    print(f"CHECK 3 {min_matrix.shape}")

    min_indices = np.argsort(min_matrix)

    # take 5 indices that corresponds to 5 smallest distance

    candidate_indices = min_indices[:5]
    print(candidate_indices)

    # set threshold
    threshold = 0.5

    # Find the indices where the value is less than or equal to 0.5
    perfect_indices = np.where(min_matrix <= threshold)[0]
    print(perfect_indices)

    for i in range(len(perfect_indices)):
        found_id = ids[perfect_indices[i]]
        foundpost = FoundPost.objects.get(id=found_id)
        score = min_matrix[perfect_indices[i]]
        # match = CandidateMatch(user = post.user,lostpost=post,foundpost=foundpost,
        #                        score = score,threshold=True)
        match,created = CandidateMatch.objects.get_or_create(user = post.user,lostpost=post,foundpost=foundpost)
        match.score = score
        match.threshold= True
        match.save()

    
    for i in range(len(candidate_indices)):
        found_id = ids[candidate_indices[i]]

        foundpost = FoundPost.objects.get(id=found_id)
        match, created = CandidateMatch.objects.get_or_create(user=post.user,
                                                              lostpost=post,
                                                                foundpost = foundpost
                                                                )
        if created:
            score = min_matrix[candidate_indices[i]]
            match.score = score
            match.threshold = False
            match.save()
            
    print('ALMOST FINISHED!')
    
    print('ALMOST FINISHED 2!')



@shared_task
def loop(l):
    "simulate a long-running task like export of data or generating a report"
    for i in range(int(l)):
        print(i)
        time.sleep(1)
    print('Task completed')

def retrievePost(lost=True):
    if lost:
        posts = LostPost.objects.all()
    else:
        posts = FoundPost.objects.all()

    embeddings = []
    ids = []
    for post in posts:
        embedding = read_file(post.embedding.path)
        embeddings.append(embedding)
        ids.append(post.id)

    # print(len(embeddings))
    # print(len(embeddings[0]))

    embeddings = np.vstack(embeddings) # of shape (n,32)
    ids = np.array(ids)

    return embeddings,ids

@shared_task
def runAllSimilar():
    """
    Run all Similar Tasks for Lost Post that has schedule = True
    """
    A,lost_ids = retrievePost(lost=True)
    B,found_ids = retrievePost(lost=False)
    print('CHECK POINT!')
    print(A.shape)
    print(B.shape)

    A_expanded = A[:, np.newaxis, :]  # shape (m, 1, 32)
    B_expanded = B[np.newaxis, :, :]  # shape (1, n, 32)

    # Step 2: Compute squared differences
    squared_diff = (A_expanded - B_expanded) ** 2  # shape (m, n, 32)

    # Step 3: Sum squared differences along the last axis
    sum_squared_diff = np.sum(squared_diff, axis=2)  # shape (m, n)

    # Step 4: Take the square root to get the Euclidean distances
    C = np.sqrt(sum_squared_diff)  # shape (m, n)
    
    # Step 5: For each row in C, take indices of 5 entries that has smallest value
    indices_of_smallest = np.argsort(C, axis=1)[:, :5] # of shape (m,5)

    # Extract the smallest values using advanced indexing
    smallest_values = np.take_along_axis(C, indices_of_smallest, axis=1)

    # Step 6: Create MatchCandidateHistory
    for i in range(len(indices_of_smallest)):
        id = lost_ids[i]
        lostpost = LostPost.objects.get(id=id)
        
        match = CandidateMatch.objects.create(user=lostpost.user,lostpost=lostpost)
        for post_idx in indices_of_smallest[i]:
            found_id = found_ids[post_idx]

            found = FoundPost.objects.get(id=found_id)
            match.matched.add(found)
    
    threshold = 0.5


    # Step 7: For each lost post, find all found posts within the threshold
    matched_dict = {}
    for i in range(C.shape[0]):
        lost_id = lost_ids[i]
        within_threshold = np.where(C[i] <= threshold)[0]
        matched_found_ids = [found_ids[idx] for idx in within_threshold]
        matched_dict[lost_id] = matched_found_ids


    for lost_id in matched_dict.keys():
        lostpost = LostPost.objects.get(id=lost_id)
        if lostpost.email:
            sendEmailtoUser(lost_id,matched_dict[lost_id])

from .models import Post, Stream
from django.utils import timezone
from datetime import timedelta


# @shared_task
# def addHotPosts():
#     """
#     Add hot posts to all streams
#     """

#     # Calculate the timestamp for 48 hours ago
#     time_threshold = timezone.now() - timedelta(hours=48)

#     # Query to retrieve the 20 posts with the highest likes, posted in the last 48 hours
#     top_posts = Post.objects.filter(
#         posted__gte=time_threshold,  # Posts from the last 48 hours
#         is_hidden=False  # Exclude hidden posts
#     ).order_by('-likes')[:20]  # Order by likes in descending order and limit to 20 posts


#     streams = Stream.objects.all()

#     for stream in streams:
        
    

 

    

    

    