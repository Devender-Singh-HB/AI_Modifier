from typing import Any
from uuid import uuid4
import git
import os
from bs4 import BeautifulSoup
import re
from pathlib import Path
import io
import ftplib
import shutil
try:
    import PIL.Image as Image
except: 
    pass

# from PIL import Image

from django.http import HttpResponse
from django.shortcuts import redirect, HttpResponseRedirect, render
from django.urls import reverse
from django.template.response import TemplateResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template import loader
from django.conf import settings

from accounts.models import ClientRequest, ChangeRequest
from modifier_admin.models import Profile

# Create path where all repos from client will be stored
REPO_DIR = os.path.join(os.path.join(Path(__file__).resolve().parent, 'static'), 'All_Repo')

def index(request: Any) -> TemplateResponse:
    """
    View for home page
    
    : args: request: Any(WSGI Requst object)
    : return: TemplateResponse: renders html page
    """   
    # Initializing context to empty dict
    context = {}
    
    # if user is authenticated 
    if request.user.is_authenticated:
        
        # Try to get relevant data about user
        try:
            
            # Message to be displayed
            context['message'] = 'Welcome to AI Modifier'
            
            # Get profile using email(unique field in Profile table)
            profile = Profile.objects.get(email=request.user.email)   
            
            # set user in context     
            context['user'] = request.user
            
            # get all request by user (if already added)
            if len(profile.client_request.all()) > 0 :
                
                # set urls in context 
                context['urls'] = [client_req.url for client_req in profile.client_request.all()]
            
            # render and pass context to the index.html to be displayed 
            return TemplateResponse(request, 'accounts/index.html', context)
        
        except Exception as e:
            # Couldn't get user
            print('No user found')
        
    # render template for login
    return TemplateResponse(request, 'accounts/index.html', {'message': 'Please login to continue.'})


def signin(request: Any) -> TemplateResponse:
    """
    Authenticate user's credentials and try logging in.
    
    : args: request: Any(WSGI Requst object)
    : return: TemplateResponse: renders html page
    """

    # check if request is post request
    if request.method == 'POST':
        
        # get user's email
        email = request.POST['email']
        
        # get user's password 
        password = request.POST['password']
        
        # authenticate user credentials
        user = authenticate(email=email, password=password)

        try:
            # login user
            login(request, user)
            
            # return to home page
            return HttpResponseRedirect(reverse('index'))
            
        # if login fails
        except Exception as e:
            print(f'Exception: {e}')
            
            # User credentials didn't match while login 
            return TemplateResponse(request, 'accounts/signin.html', {'message':'Invalid Credentials'})
    
    # return login page 
    return TemplateResponse(request, 'accounts/signin.html')

def add_request(request: Any) -> TemplateResponse:
    """
    Add and update user's request.
    
    : args: request: Any(WSGI Requst object)
    : return: TemplateResponse: renders html page
    """
    
    # if request is post request
    if request.method == 'POST':
        
        # find if user request already exists and update it
        try:
            
            # check if user request exists
            if ClientRequest.objects.filter(url=request.POST['url']).exists():
                
                # filter out client request and all fields 
                ClientRequest.objects.filter(url=request.POST['url']).update(
                    url=request.POST['url'],
                    code_link=request.POST['link'],
                    username=request.POST['username'],
                    token=request.POST['token'],
                    version_control=request.POST['version_control'],
                    branch=request.POST['branch'],
                    port=request.POST['port'],
                    profile=Profile.objects.get(email=request.POST['email'])
                )
                
                
            else:
                
                # user request didn't exists, so create new user request
                instance = ClientRequest(url=request.POST['url'],
                                        code_link=request.POST['link'],
                                        username=request.POST['username'],
                                        token=request.POST['token'],
                                        version_control=request.POST['version_control'],
                                        branch=request.POST['branch'],
                                        port=request.POST['port'],
                                        profile=Profile.objects.get(email=request.POST['email']))
                
                # save user request
                instance.save()
            
            # return to home page
            return HttpResponseRedirect(reverse('index'))
        
        # something went wrong while updating or adding request
        except Exception as e:
            print(f'Some exception occurred: {e}')
            
            # render add_request.html page with fail to "create request" message
            return TemplateResponse(request, 'accounts/add_request.html', {'message': 'Could not add request. Try Again!'})
    
    # render add_request.html page with "add new request" message.
    return TemplateResponse(request, 'accounts/add_request.html', {'message': 'Add new request'})


def get_images(dir: str, dir_level:int) -> list:
    """
    Check all directories within 'dir' and get all images(jpg,png and jpeg).
    
    :args : dir: path to directory where images will be searched
    """
    
    # initialize results
    res = []
    
    # explore 'dir' and all contents winthin it 
    for root, dirnames, filenames in os.walk(dir):
        
        # for all files found in 'filenames'
        for filename in filenames:
            file_level = len(root.split('/')) + 1
            # check if filname is an images
            if file_level == dir_level and (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
                
                # add image's path to the result
                # res.append([filename, os.path.join(root, filename)])
                print(f'{root}/{filename}')
                res.append(filename)
    
    # return result       
    return res
    

def get_all_images(soup: BeautifulSoup, img_list: list) -> list:
    """
    Get all images from 'soup' object and find all other images at the same level 
    
    :args: soup: BeautifulSoup object loaded with html file, parsed using html parser
         : img_list: list of all images within the repo.
         
    : returns: list conatining all information about all images within soup
    """
    
    # Initialize results
    response_table = []
    
    # dir = os.path.join(settings.BASE_DIR, repo_name)
    
    # find all 'img' Tags and index them
    for idx, img in enumerate(soup.find_all('img')):
        try:
            # get image path from img_list
            for img_list_element in img_list:
                
                # check if img_list_element ends with 'image source'
                if img_list_element.endswith(img['src']):
                    
                    # found image location and adding 'tag', 'current image source',
                    # 'all other images in that directory' and 'index of img' soup element.
                    file_path = os.path.join(REPO_DIR, img_list_element)
                    response_table.append([img_list_element.split('/')[-1].split('.')[0], 
                                           {'src': os.path.join('All_Repo', img_list_element), 
                                            'available_images': get_images(file_path[:file_path.rfind('/')], len(file_path.split('/')))}, 
                                           idx])
                    
        except Exception as e: 
            print(e)
            
    # return response table
    return response_table


def get_all_web_elements(soup: BeautifulSoup) -> list:
    """
    Find all static text and their style property if exists.
    
    : args: soup: BeautifulSoup object loaded with html file, parsed using html parser
    
    : returns: list of all static text found in soup.
    """
    
    # Initialize results
    response_Table = []
    
    tags = ['style', 'script', 'head', 'meta', '[document]']
    
    # get all web elements
    for idx, x in enumerate(soup.find_all(tag='', text=re.compile(''))):
        # remove ankle brackets
        tag = str(x).split("<")[1].split(">")[0]
        
        # split web element string at " "
        if " " in tag: tag = tag.split(" ")[0]
        
        if tag not in tags:
        
            # get web element's string
            soup_string = str(x.string)
            
            # if web element is dynamic i.e., have {{ some variable }}, skip it
            if "{{" in soup_string and "}}" in soup_string: continue
            
            # convert string
            text = str(x)
            
            # if font-size is present in web element 
            if text.find("font-size") != -1:
                
                # extract font-size's value 
                size = str(text.split("font-size:")[1].split("px;")[0])
                
            # else set it to ""
            else:
                size = ""
                
            # if color is present in web element
            if text.find("color") != -1:
                
                # extract color's value
                color = text.split("color:")[1].split(";")[0]
                
            # else set it to ""
            else:
                color = ""
                
            # create attribute list of web element
            temp = [tag, soup_string.strip(), text ,size, color, idx]
            
            # append attribute list to Response_Table
            response_Table.append(temp)
    
    return response_Table
        
    # Remove duplicates from Response_Table        
    # temp = []
    # for x in Response_Table:
    #     if x not in temp:
    #         temp.append(x)
            
    # return temp
    
def download_files(ftp, path, destination):

    path = path[:-1] if path[-1] == '/' else path

    try:
        folder = path[path.rfind('/')+1:]
        destination = os.path.join(destination, folder)
        if not os.path.exists(destination):
            os.makedirs(destination)
                
    except ftplib.error_perm:
        pass
        
    for file in ftp.nlst():
        try:
            #this will check if file is folder:
            new_dest = f'{path}/{file}'
            ftp.cwd(file)
            #if so, explore it:
            download_files(ftp, new_dest, destination)
            ftp.cwd('..')
        except ftplib.error_perm:
            if file.endswith('.html') or file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg'):
                with open(os.path.join(destination,file),"wb") as f:
                    ftp.retrbinary("RETR "+file, f.write)
            
    return

def change_request(request: Any) -> TemplateResponse:
    """
    Handles change request for website 
    
    : args: request: Any(WSGI Requst object)
    : return: TemplateResponse: renders html page
    """
    
    # if request is post request
    if request.method == 'POST':
        try:
            
            # get ClientRequest obeject from 'client_req_urls'
            client_request = ClientRequest.objects.get(url=request.POST['client_req_urls'])
            
            # get all fields
            url = client_request.url
            code_link = client_request.code_link
            username = client_request.username
            token = client_request.token
            version_control = client_request.version_control
            branch = client_request.branch
            port = client_request.port
            profile = client_request.profile
            
            # if version control is FTP
            Repo_Name = os.path.join(REPO_DIR, branch[branch.rfind('/')+1:]) \
                            if version_control.lower() == 'ftp' \
                            else os.path.join(REPO_DIR, code_link[code_link.rfind('/')+1:].split('.')[0])

            # if user pressed 'Edit Request' btn render add_request.html
            if 'edit_request' in request.POST:
                return TemplateResponse(request, 
                                        "accounts/add_request.html", 
                                        {'message': 'Edit Request',
                                         'url': url,
                                         'code_link': code_link,
                                         'username': username,
                                         'token': token,
                                         'version_control': version_control,
                                         'branch': branch,
                                         'port': port,
                                         'profile': profile,
                                         'edit_request': 'edit_request'
                                         })
                
            else:
                # Initialize 
                msg = ""
                save_btn = "save"
                content_btn = "text"
                tags = ['style', 'script', 'head', 'title', 'meta', '[document]']
                
                # check is 'Path_To_Search' in form
                if 'Path_To_Search' in request.POST:                    
                    # get 'Path_To_Search' value 
                    Path_To_Search = os.path.join(REPO_DIR, request.POST['Path_To_Search'])
                else:
                    Path_To_Search = None
                
                # Set Response_Table to empty list
                Response_Table = []
                Response_Table_Length = len(Response_Table)
                
                # Set Response_Image_Table to empty list
                Response_Image_Table = []
                Response_Image_Table_Length = len(Response_Image_Table)
                
                # if version_control.lower() == 'ftp':
                #     Repo_Path = code_link.replace('//',f'//{username}:{token}@')
                #     # Set branch
                #     Branch_Name = branch
                    
                #     # Extract Repo Name from url
                #     Repo_Name = os.path.join(REPO_DIR, Repo_Path[Repo_Path.rfind('/')+1:].split('.')[0])
                    
                # else:
                #     # Create url to get repository
                #     # Repo_Path = f"{code_link[:code_link.find('//')+2]}{username}:{token}@{code_link[code_link.find('//')+2:]}"
                #     Repo_Path = code_link.replace('//',f'//{username}:{token}@')
                #     # Set branch
                #     Branch_Name = branch
                    
                #     # Extract Repo Name from url
                #     Repo_Name = os.path.join(REPO_DIR, Repo_Path[Repo_Path.rfind('/')+1:].split('.')[0])
                
                
                Html_List = []
                img_list = []
                for root, dirnames, filenames in os.walk(Repo_Name):
                    for filename in filenames:
                        if filename.endswith('.html'):
                            # Html_List.append([filename, os.path.join(root, filename)])
                            
                            file_path = os.path.join(root, filename)
                            if file_path:
                                
                                Html_List.append([filename, file_path[len(REPO_DIR)+1:]])
                            
                        elif filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                            # img_list.append(os.path.join(root, filename))
                            
                            file_path = os.path.join(root, filename)
                            if file_path:
                                
                                img_list.append(file_path[len(REPO_DIR)+1:])
                
                # if 'Repo_Path' in request.POST and 'Branch_Name' in request.POST and 'Page_Name' not in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                if 'make_changes' in request.POST:
                    
                    if version_control.lower() == 'ftp':
                        
                        if os.path.exists(Repo_Name):
                            # os.rmdir(Repo_Name)
                            shutil.rmtree(Repo_Name)
                            
                        # create FTP instance 
                        ftp = ftplib.FTP()
                        
                        # connect to ftp server
                        ftp.connect(host=code_link, port=int(port))
                        
                        # Login to server
                        ftp.login(username, token)
                        
                        # change to location to source
                        ftp.cwd(branch)
                        
                        # download all files to REPO_DIR (All_Repo)
                        download_files(ftp, branch, REPO_DIR)
                        
                        ftp.quit()
                        
                    else:
                        
                        Repo_Path = code_link.replace('//',f'//{username}:{token}@')
                        
                        # Auto pull remote repository and change branch
                        if not(os.path.exists(REPO_DIR)):
                            os.makedirs(REPO_DIR)

                        if not(os.path.exists(Repo_Name)):
                            repo = git.Repo.clone_from(Repo_Path, Repo_Name)
                            
                        else:
                            repo = git.Repo(Repo_Name)
                            repo.git.reset("--hard")
                            
                        repo.git.checkout(branch)
                        repo.git.pull()
                    
                    Html_List = []
                    img_list = []
                    for root, dirnames, filenames in os.walk(Repo_Name):
                        for filename in filenames:
                            if filename.endswith('.html'):
                                # Html_List.append([filename, os.path.join(root, filename)])
                                
                                file_path = os.path.join(root, filename)
                                if file_path:
                                                      
                                    Html_List.append([filename, file_path[len(REPO_DIR)+1:]])
                                
                            elif filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                                # img_list.append(os.path.join(root, filename))
                                
                                file_path = os.path.join(root, filename)
                                if file_path:
                                    
                                    img_list.append(file_path[len(REPO_DIR)+1:])
                
                elif 'Page_Name' in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                    
                    # Pull all the Editable content from the HTML page
                    Path_To_Search = os.path.join(REPO_DIR, request.POST['Page_Name'])
                    
                    if 'find' in request.POST:
                        with open(Path_To_Search) as fp:
                            soup = BeautifulSoup(fp, 'html.parser')
                
                            # tags = ['style', 'script', 'head', 'title', 'meta', '[document]']
                            # tags = ['style']
                            # for t in tags:
                            #     [s.extract() for s in soup(t)]
                            
                            # get response table
                            Response_Table = get_all_web_elements(soup=soup)                        
                            Response_Table_Length = len(Response_Table)
                    
                    elif 'img' in request.POST:
                        with open(Path_To_Search) as fp:
                            soup = BeautifulSoup(fp, 'html.parser')
                            
                            # get response table
                            Response_Image_Table = get_all_images(soup=soup,  
                                                                  img_list=img_list)   
                            
                            Response_Image_Table_Length = len(Response_Image_Table)
                    
                # elif 'Replace_Text_With' in request.POST and 'Text_To_Replace' in request.POST and 'Where_To_Change' in request.POST:
                elif 'Replace_Text_With' in request.POST:
                    
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser')
                        
                    # Where_To_Change = request.POST['Where_To_Change']
                    # Text_To_Replace = request.POST['Text_To_Replace']
                    Replace_Text_With = request.POST['Replace_Text_With']
                    Replace_Font_With = request.POST['Replace_Font_With']
                    Replace_Color_With = request.POST['Replace_Color_With']
                    color_change = request.POST['color_change']
                    
                    # for t in tags:
                    #     [s.extract() for s in soup(t)]
                    
                    elements = soup.find_all(tag='', text=re.compile(''))
                    element = elements[int(request.POST['index'])]
                    
                    print(f'Text: {element.text}')
                    
                    
                    if element.has_attr('style'):
                        print(element['style'])
                        style = element['style']
                        
                        style = style.split(';')
                        new_style = []
                        for style_attr in style:
                            if color_change != 'false' and style_attr.split(':')[0] == 'color':
                                new_style.append(f'color:{Replace_Color_With}')
                                
                            elif Replace_Font_With != '' and style_attr.split(':')[0] == 'font-size':
                                new_style.append(f'font-size:{Replace_Font_With}px')
                            
                            else:
                                new_style.append(style_attr)
                        
                        print(new_style)
                        new_style = ';'.join(new_style)
                        
                        if color_change != 'false' and new_style.find('color') == -1:
                            new_style += f'color:{Replace_Color_With};'
                        
                        if Replace_Font_With != '' and new_style.find('font-size') == -1:
                            new_style += f'font-size:{Replace_Font_With}px;'
                        
                        element['style'] = new_style
                        print(element['style'])
                        
                    elif color_change != 'false' or Replace_Font_With != '':
                        attribute = ''
                        if color_change != 'false':
                            attribute += f'color:{Replace_Color_With};'
                        
                        if Replace_Font_With != '':
                            attribute += f'font-size:{Replace_Font_With}px;'
                        
                        element['style'] = attribute
                        
                        print(element['style'])
                        
                    # element.string = element.string.replace(Text_To_Replace,Replace_Text_With)
                    element.string = Replace_Text_With
                    print(f'Text: {element.text}')
                    
                    with open(Path_To_Search, "w") as fp:
                        fp.write(soup.prettify())
                    
                    msg = "Success. Please push the changes"
                    
                    Response_Table = get_all_web_elements(soup)
                    Response_Table_Length = len(Response_Table)
                    save_btn = "undo"
                    
                    
                elif 'current_src' in request.POST:
                    
                    # Check if atleast one of the option is present 
                    # either image is selected or image is uploaded
                    if request.POST['available_images'] != "select_availaible_image" or len(request.FILES) != 0:
                        
                        # open Path_To_Search html file 
                        with open(Path_To_Search) as fp:
                            original_soup = BeautifulSoup(fp, 'html.parser')
                        
                        # Initialize width and height to None
                        width, height = None, None
                        
                        # Check if width is present in request   
                        if request.POST['width'] != '':
                            
                            # set width
                            width = int(request.POST['width'])
                            
                        # Check if height is present in request
                        if request.POST['height'] != '':
                            
                            # set height
                            height = int(request.POST['height'])
                        
                        # Initialize file_exists to None
                        file_exists = False
                        
                        # get current source of image relative to repository
                        current_src = request.POST['current_src']
                        
                        # If image is uploaded by user
                        if request.POST['available_images'] == "select_availaible_image":
                            
                            # get image name 
                            name = request.FILES["filename"].name
                            
                            # reading and saving the image in the same directory as current image
                            image_location = f"{REPO_DIR[:REPO_DIR.rfind('All_Repo')]}{current_src[:current_src.rfind('/')+1]}{name}"
                            
                            # check if image is not already present in that directory
                            if not os.path.exists(image_location):
                                
                                # try and save image 
                                try:
                                    
                                    # read image data from Bytes
                                    image = Image.open(io.BytesIO(request.FILES["filename"].file.read()))
                                    
                                    # save image to location
                                    image.save(image_location)
                                    
                                    # append newly created image to image_list
                                    img_list.append(image_location[len(REPO_DIR)+1:])
                                except:
                                    pass

                            else:
                                
                                # image already exists, set file_exists to True
                                file_exists = True
                            
                        # image is selected from dropdown
                        else:
                            
                            # get image name 
                            name = request.POST['available_images'].split('/')[-1]
                        
                        # set message and save_btn value for html rendering
                        msg = "Success. Please push the changes"
                        save_btn = "undo"
                        
                        # Change value of message and save_btn if file already exists
                        if file_exists:
                            msg = "File already exists with same name. Please change file name."
                            save_btn = "save"   
                            
                        # Change source of image tag 
                        else:
                            
                            # get img tag at index
                            image_to_change = original_soup.find_all('img')[int(request.POST['index'])]
                            
                            # construct new source path 
                            new_src = f"{image_to_change['src'][:image_to_change['src'].rfind('/')+1]}{name}"
                            
                            # set new source path to selected image
                            image_to_change['src'] = new_src

                            # if width is not None
                            if width:
                                
                                # set width value
                                image_to_change['width'] = width
                            
                            # if height is not None
                            if height:
                                
                                # set height value
                                image_to_change['height'] = height

                            # write changed contents to the html file
                            with open(Path_To_Search, "w") as fp:
                                    fp.write(original_soup.prettify())
                                    
                    # Nither image is selected from dropdown, nor image is uploaded
                    else:
                        msg = "Please select image from dropdown or upload an image"
                        save_btn = "save"
                    
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser') 
                        
                        
                        Response_Image_Table = get_all_images(soup=soup,  
                                                              img_list=img_list)   
                                                    
                        Response_Image_Table_Length = len(Response_Image_Table)

                  
                elif 'save' in request.POST and 'push' not in request.POST:
                    
                    # Write the soup to the source file or Undo saved changes
                    save_btn = request.POST['save']
                    if save_btn == "save":
                        with open(Path_To_Search, "w") as fp:
                            original_soup = original_soup.prettify()
                            fp.write(original_soup)
                        # repo.git.add(update=True)
                        # repo.index.commit(Commit_Message)
                        msg = "Success. Please push the changes"
                        save_btn = "undo"
                        
                    else:
                        repo = git.Repo(Repo_Name)
                        repo.git.stash("save")
                        msg = "Changes successfully restored"
                        save_btn = "save"
                    
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser')
                    # tags = ['style']
                    # for t in tags:
                    #     [s.extract() for s in soup(t)]
                    
                    Response_Table = get_all_web_elements(soup)
                    Response_Table_Length = len(Response_Table)
                    
                    
                elif 'push' in request.POST:
                    
                    try:
                        change_request = ChangeRequest(client_request=client_request, repo=Repo_Name)
                        change_request.save()
                        msg = "Changes have been pushed successfully"
                    except:
                        msg = "Failed to push changes!"
                        
                    
                return TemplateResponse(request, 
                                        "accounts/change_request.html", 
                                        {'user':profile, 
                                         'repo':code_link, 
                                         'branch':branch, 
                                         'Html_List':Html_List, 
                                         'Text_Table':Response_Table, 
                                         'Text_Table_Length':Response_Table_Length,
                                         'Image_Table':Response_Image_Table, 
                                         'Image_Table_Length':Response_Image_Table_Length,
                                         'msg':msg, 
                                         'save_btn':save_btn, 
                                         'client_req_urls':request.POST['client_req_urls'],
                                         'Path_To_Search': Path_To_Search[len(REPO_DIR)+1:] if Path_To_Search is not None else Path_To_Search},
                                        )
        
        except Exception as e:
            print(f'Some exception has occured: {e}')
            
    return redirect("index")


def password_reset_request(request):

    if request.method == "POST":
     
        password_reset_form = PasswordResetForm(request.POST)
        
        if password_reset_form.is_valid():
      
            email = password_reset_form.cleaned_data['email']
   
            users = Profile.objects.filter(email=email)
            
            if users.exists():
                user = users[0]
                print(email)
                
                subject = "Password Reset Requested"
                email_template_name = "accounts/password_reset_email.txt"
                c = {
                "email":email,
                'domain':'127.0.0.1:8000',
                'site_name': 'Website',
                "uid": urlsafe_base64_encode(force_bytes(user.email)),
                'token': default_token_generator.make_token(user),
                'protocol': 'http',
                }
                created_email = render_to_string(email_template_name, c)
                print(created_email)
                try:
                    # send_mail(subject, email, 'admin@example.com' , [user.email], fail_silently=False)
                    pass
                except Exception as e:
                    return HttpResponse('Invalid header found.')
            
                return redirect("index")
            
    password_reset_form = PasswordResetForm()
    
    return TemplateResponse(request, "accounts/password_reset.html", {"password_reset_form":password_reset_form})    
    

def signout(request):
    print('View for signout\n')

    logout(request)
    # return TemplateResponse(request, 'accounts/index.html', {'message': 'Logged Out'})
    return redirect("index")