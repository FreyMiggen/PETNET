### CREATE EMBEDDING FILE FOR FOUND POSTS
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '3'
import tensorflow as tf 
import numpy as np 
from utils import process_img_batch,_pairwise_distances,init_model


def create_embedding(datadir,model_fol):
    
    model_path= os.path.join(model_fol,'resnet_50v2_emb_32_margin_02_alpha_05_60_epoch.h5')
    model = init_model()
    model.load_weights(model_path)

    # in folder has 32 sub
    foldir=[os.path.join(datadir,filename) for filename in os.listdir(datadir)]

    for sub_dir in foldir:
        img_paths = [os.path.join(sub_dir,filename) for filename in os.listdir(sub_dir)]
        cat_emb = process_img_batch(img_paths,model)
        dist_cat= _pairwise_distances(cat_emb, squared=False)[0]
        mean_emb=np.mean(dist_cat,axis=0)
        ind=np.argsort(mean_emb)

        # SAVE ONE EMBEDDING VECTOR THAT HAS THE BEST REPRESENTATIVE POWER
        data=cat_emb[ind[0]] # of shape (1,32)
        # save to a byte file
        saved_name = os.path.basename(sub_dir)
        saved_name = f"found_emb/{saved_name}.npy"
        with open(saved_name,'wb') as f:
            np.save(f,data)

datadir= r'C:\Users\ADMIN\Documents\AI\CAT-FACE-VERI\Cat-Face-Verification\0\0'

model_fol = r'C:\Users\ADMIN\OneDrive - Hanoi University of Science and Technology\WEB\django\test_4\resnet' 

create_embedding(datadir,model_fol)
