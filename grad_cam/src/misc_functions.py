"""
Created on Thu Oct 21 11:09:09 2017

@author: Utku Ozbulak - github.com/utkuozbulak
"""
import os
import copy
import numpy as np
from PIL import Image
import matplotlib.cm as mpl_color_map
import cv2
import torch
from torch.autograd import Variable
from torchvision import models
from os.path import dirname, abspath, join
from net import Net

PROJECT_FILE_DIR = dirname(dirname(abspath(__file__)))


def convert_to_grayscale(im_as_arr):
    """
        Converts 3d image to grayscale

    Args:
        im_as_arr (numpy arr): RGB image with shape (D,W,H)

    returns:
        grayscale_im (numpy_arr): Grayscale image with shape (1,W,D)
    """
    grayscale_im = np.sum(np.abs(im_as_arr), axis=0)
    im_max = np.percentile(grayscale_im, 99)
    im_min = np.min(grayscale_im)
    grayscale_im = (np.clip((grayscale_im - im_min) / (im_max - im_min), 0, 1))
    grayscale_im = np.expand_dims(grayscale_im, axis=0)
    return grayscale_im


def save_gradient_images(gradient, file_name):
    """
        Exports the original gradient image

    Args:
        gradient (np arr): Numpy array of the gradient with shape (3, 224, 224)
        file_name (str): File name to be exported
    """
    if not os.path.exists(join(PROJECT_FILE_DIR, 'results')):
        os.makedirs(join(PROJECT_FILE_DIR, 'results'))
    # Normalize
    gradient = gradient - gradient.min()
    gradient /= gradient.max()
    # Save image
    path_to_file = os.path.join(PROJECT_FILE_DIR, 'results', file_name + '.jpg')
    save_image(gradient, path_to_file)


def save_class_activation_images(org_img, activation_map, file_name):
    """
        Saves cam activation map and activation map on the original image

    Args:
        org_img (PIL img): Original image
        activation_map (numpy arr): Activation map (grayscale) 0-255
        file_name (str): File name of the exported image
    """
    if not os.path.exists('../results'):
        os.makedirs('../results')
    # Grayscale activation map
    heatmap, heatmap_on_image = apply_colormap_on_image(org_img, activation_map, 'hsv')
    # Save colored heatmap
    path_to_file = os.path.join('../results', file_name + '_Cam_Heatmap.png')
    print(np.max(heatmap))
    save_image(heatmap, path_to_file)
    # Save heatmap on iamge
    print()
    print(np.max(heatmap_on_image))
    path_to_file = os.path.join('../results', file_name + '_Cam_On_Image.png')
    save_image(heatmap_on_image, path_to_file)
    # SAve grayscale heatmap
    print()
    print(np.max(activation_map))
    path_to_file = os.path.join('../results', file_name + '_Cam_Grayscale.png')
    save_image(activation_map, path_to_file)


def apply_colormap_on_image(org_im, activation, colormap_name):
    """
        Apply heatmap on image
    Args:
        org_img (PIL img): Original image
        activation_map (numpy arr): Activation map (grayscale) 0-255
        colormap_name (str): Name of the colormap
    """
    # Get colormap
    color_map = mpl_color_map.get_cmap(colormap_name)
    no_trans_heatmap = color_map(activation)
    # Change alpha channel in colormap to make sure original image is displayed
    heatmap = copy.copy(no_trans_heatmap)
    heatmap[:, :, 3] = 0.4
    heatmap = Image.fromarray((heatmap * 255).astype(np.uint8))
    no_trans_heatmap = Image.fromarray((no_trans_heatmap * 255).astype(np.uint8))

    # Apply heatmap on iamge
    heatmap_on_image = Image.new("RGBA", org_im.size)
    heatmap_on_image = Image.alpha_composite(heatmap_on_image, org_im.convert('RGBA'))
    heatmap_on_image = Image.alpha_composite(heatmap_on_image, heatmap)
    return no_trans_heatmap, heatmap_on_image


def save_image(im, path):
    """
        Saves a numpy matrix of shape D(1 or 3) x W x H as an image
    Args:
        im_as_arr (Numpy array): Matrix of shape DxWxH
        path (str): Path to the image

    TODO: Streamline image saving, it is ugly.
    """
    if isinstance(im, np.ndarray):
        if len(im.shape) == 2:
            im = np.expand_dims(im, axis=0)
            print('3_channel_image')
            print(im.shape)
        if im.shape[0] == 1:
            # Converting an image with depth = 1 to depth = 3, repeating the same values
            # For some reason PIL complains when I want to save channel image as jpg without
            # additional format in the .save()
            print('1_channel_image')
            im = np.repeat(im, 3, axis=0)
            print(im.shape)
            # Convert to values to range 1-255 and W,H, D
        # A bandaid fix to an issue with gradcam
        if im.shape[0] == 3 and np.max(im) == 1:
            im = im.transpose(1, 2, 0) * 255
        elif im.shape[0] == 3 and np.max(im) > 1:
            im = im.transpose(1, 2, 0)
        im = Image.fromarray(im.astype(np.uint8))
    im.save(path)


def preprocess_image(pil_im, resize_im=True):
    """
        Processes image for CNNs

    Args:
        PIL_img (PIL_img): Image to process
        resize_im (bool): Resize to 224 or not
    returns:
        im_as_var (torch variable): Variable that contains processed float tensor
    """
    # mean and std list for channels (Imagenet)
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    # Resize image
    if resize_im:
        pil_im.thumbnail((224, 224))
    im_as_arr = np.float32(pil_im)
    im_as_arr = im_as_arr.transpose(2, 0, 1)  # Convert array to D,W,H
    # Normalize the channels
    for channel, _ in enumerate(im_as_arr):
        im_as_arr[channel] /= 255
        im_as_arr[channel] -= mean[channel]
        im_as_arr[channel] /= std[channel]
    # Convert to float tensor
    im_as_ten = torch.from_numpy(im_as_arr).float()
    # Add one more channel to the beginning. Tensor shape = 1,3,224,224
    im_as_ten.unsqueeze_(0)
    # Convert to Pytorch variable
    im_as_var = Variable(im_as_ten, requires_grad=True)
    return im_as_var


def recreate_image(im_as_var):
    """
        Recreates images from a torch variable, sort of reverse preprocessing
    Args:
        im_as_var (torch variable): Image to recreate
    returns:
        recreated_im (numpy arr): Recreated image in array
    """
    reverse_mean = [-0.485, -0.456, -0.406]
    reverse_std = [1 / 0.229, 1 / 0.224, 1 / 0.225]
    recreated_im = copy.copy(im_as_var.data.numpy()[0])
    for c in range(3):
        recreated_im[c] /= reverse_std[c]
        recreated_im[c] -= reverse_mean[c]
    recreated_im[recreated_im > 1] = 1
    recreated_im[recreated_im < 0] = 0
    recreated_im = np.round(recreated_im * 255)

    recreated_im = np.uint8(recreated_im).transpose(1, 2, 0)
    return recreated_im


def get_positive_negative_saliency(gradient):
    """
        Generates positive and negative saliency maps based on the gradient
    Args:
        gradient (numpy arr): Gradient of the operation to visualize

    returns:
        pos_saliency ( )
    """
    pos_saliency = (np.maximum(0, gradient) / gradient.max())
    neg_saliency = (np.maximum(0, -gradient) / -gradient.min())
    return pos_saliency, neg_saliency


def get_example_params(class_no, image_no, check_target_class):
    """
        Gets used variables for almost all visualizations, like the image, model etc.

    Args:
        example_index (int): Image id to use from examples

    returns:
        original_image (numpy arr): Original image read from the file
        prep_img (numpy_arr): Processed image
        target_class (int): Target class for the image
        file_name_to_export (string): File name to export the visualizations
        pretrained_model(Pytorch model): Model to use for the operations
    """

    # class_list=[
    # "agricultural" ,        # class_num =0
    # "airplane" ,            # class_num =1
    # "baseballdiamond" ,     # class_num =2
    # "beach" ,               # class_num =3
    # "buildings" ,           # class_num =4
    # "chaparral" ,           # class_num =5
    # "denseresidential" ,    # class_num =6
    # "forest" ,              # class_num =7
    # "freeway" ,             # class_num =8
    # "golfcourse" ,          # class_num =9
    # "harbor" ,              # class_num =10
    # "intersection" ,        # class_num =11
    # "mediumresidential" ,   # class_num =12
    # "mobilehomepark" ,      # class_num =13
    # "overpass" ,            # class_num =14
    # "parkinglot" ,          # class_num =15
    # "river" ,               # class_num =16
    # "runway" ,              # class_num =17
    # "sparseresidential" ,   # class_num =18
    # "storagetanks" ,        # class_num =19
    # "tenniscourt"]          # class_num =20

    # Pick one of the examples
    # path_to_test_folder =  join(PROJECT_FILE_DIR, "data")
    # print('###################################',path_to_test_folder)
    # img_path  = join(path_to_test_folder, class_list[class_no], class_list[class_no] + str(image_no)+".tif")
    # print img_path

    # overide image path for testing
    custom_path = join(PROJECT_FILE_DIR, "inputs/vgg_224.png")
    img_path = custom_path

    target_class = check_target_class
    file_name_to_export = img_path[img_path.rfind('/') + 1:img_path.rfind('.')]

    # Read image
    original_image = Image.open(img_path).convert('RGB')

    # Process image
    prep_img = preprocess_image(original_image)

    # Define model
    # sftp://test1@10.107.42.42/home/Drive2/amil/grad_cam/grad_cam/state_dict.pt
    # path_weights = join(PROJECT_FILE_DIR, "model.pt")
    # path_model = join(PROJECT_FILE_DIR, "state_dict.pt")
    # from 
    path_model = join(PROJECT_FILE_DIR, "vgg_models/model.pt")
    path_weights = join(PROJECT_FILE_DIR, "vgg_models/statedict.pt")

    checkpoint = torch.load(path_weights, map_location="cpu")
    pretrained_model = torch.load(path_model, map_location="cpu")
    # pretrained_model = Net()
    pretrained_model.load_state_dict(checkpoint)

    return (original_image,
            prep_img,
            target_class,
            file_name_to_export,
            pretrained_model)
