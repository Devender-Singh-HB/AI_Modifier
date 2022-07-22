from typing import Any
from uuid import uuid4
import git
import os
from bs4 import BeautifulSoup
import re
from pathlib import Path
import io
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


def get_images(dir: str) -> list:
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
            
            # check if filname is an images
            if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                
                # add image's path to the result
                res.append([filename, os.path.join(root, filename)])
    
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
                    response_table.append([img_list_element.split('/')[-1].split('.')[0], 
                                           {'src': img_list_element[len(REPO_DIR)-8:], 
                                            'available_images': get_images(img_list_element[:img_list_element.rfind('/')])}, 
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
    
    # get all web elements
    for idx, x in enumerate(soup.find_all(tag='', text=re.compile(''))):
        # remove ankle brackets
        tag = str(x).split("<")[1].split(">")[0]
        
        # split web element string at " "
        if " " in tag: tag = tag.split(" ")[0]
        
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
        temp = [tag, soup_string, text ,size, color, idx]
        
        # append attribute list to Response_Table
        response_Table.append(temp)
    
    return response_Table
        
    # Remove duplicates from Response_Table        
    # temp = []
    # for x in Response_Table:
    #     if x not in temp:
    #         temp.append(x)
            
    # return temp

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
            profile = client_request.profile
            
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
                                         'profile': profile,
                                         'edit_request': 'edit_request'
                                         })
                
            else:
                # global Repo_Path
                # global Repo_Name
                # global Branch_Name
                # global Text_To_Replace
                # global Path_To_Search
                # global Response_Table
                # global Response_Table_Length
                # global original_soup
                # global soup
                # global repo
                # global save_btn
                # global content_btn
                # global Html_List
                
                # Initialize 
                msg = ""
                save_btn = "save"
                content_btn = "text"
                
                # check is 'Path_To_Search' in form
                if 'Path_To_Search' in request.POST:
                    
                    # get 'Path_To_Search' value 
                    Path_To_Search = request.POST['Path_To_Search']
                else:
                    Path_To_Search = None
                
                # Set Response_Table to empty list
                Response_Table = []
                Response_Table_Length = len(Response_Table)
                
                # Set Response_Image_Table to empty list
                Response_Image_Table = []
                Response_Image_Table_Length = len(Response_Image_Table)
                
                # Create url to get repository
                Repo_Path = f"{code_link[:code_link.find('//')+2]}{username}:{token}@{code_link[code_link.find('//')+2:]}"
                
                # Set branch
                Branch_Name = branch
                
                # Extract Repo Name from url
                Repo_Name = os.path.join(REPO_DIR, Repo_Path[Repo_Path.rfind('/')+1:].split('.')[0])
                
                
                Html_List = []
                img_list = []
                for root, dirnames, filenames in os.walk(Repo_Name):
                    for filename in filenames:
                        if filename.endswith('.html'):
                            Html_List.append([filename, os.path.join(root, filename)])
                            
                        elif filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                            img_list.append(os.path.join(root, filename))
                
                # if 'Repo_Path' in request.POST and 'Branch_Name' in request.POST and 'Page_Name' not in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                if 'make_changes' in request.POST:
                    
                    # Auto pull remote repository and change branch
                    if not(os.path.exists(REPO_DIR)):
                        os.makedirs(REPO_DIR)

                    if not(os.path.exists(Repo_Name)):
                        repo = git.Repo.clone_from(Repo_Path, Repo_Name)
                        
                    else:
                        repo = git.Repo(Repo_Name)
                        repo.git.reset("--hard")
                        
                    repo.git.checkout(Branch_Name)
                    repo.git.pull()
                    
                    if len(Html_List) == 0 or len(img_list) == 0:
                        for root, dirnames, filenames in os.walk(Repo_Name):
                            for filename in filenames:
                                if filename.endswith('.html'):
                                    Html_List.append(os.path.join(root, filename))
                                    
                                elif filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                                    img_list.append(os.path.join(root, filename))
                
                elif 'Page_Name' in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                    
                    # Pull all the Editable content from the HTML page
                    Path_To_Search = request.POST['Page_Name']
                    
                    if 'find' in request.POST:
                        with open(Path_To_Search) as fp:
                            soup = BeautifulSoup(fp, 'html.parser')
                
                            # tags = ['style', 'script', 'head', 'title', 'meta', '[document]']
                            tags = ['style']
                            for t in tags:
                                [s.extract() for s in soup(t)]
                            
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
                    
                elif 'Replace_Text_With' in request.POST and 'Text_To_Replace' in request.POST and 'Where_To_Change' in request.POST:
                    
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser')
                        
                    Where_To_Change = request.POST['Where_To_Change']
                    Text_To_Replace = request.POST['Text_To_Replace']
                    Replace_Text_With = request.POST['Replace_Text_With']
                    Replace_Font_With = request.POST['Replace_Font_With']
                    Replace_Color_With = request.POST['Replace_Color_With']
                    color_change = request.POST['color_change']
                    
                    for t in ['style']:
                        [s.extract() for s in soup(t)]
                    
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
                        
                    element.string = element.string.replace(Text_To_Replace,Replace_Text_With)
                    print(f'Text: {element.text}')
                    
                    with open(Path_To_Search, "w") as fp:
                        fp.write(soup.prettify())
                    
                    msg = "Success. Please push the changes"
                    
                    Response_Table = get_all_web_elements(soup)
                    Response_Table_Length = len(Response_Table)
                    save_btn = "undo"
                    
                    # Replace the text in the soup
                    # save_btn = "save"
                    # with open(Path_To_Search) as fp:
                    #     original_soup = BeautifulSoup(fp, 'html.parser')
                    #     soup = original_soup
                    # Where_To_Change = request.POST['Where_To_Change'].replace('\r', '')
                    # Old_font = str(Where_To_Change)
                    # Text_To_Replace = request.POST['Text_To_Replace']
                    # Replace_Text_With = request.POST['Replace_Text_With']
                    # Where_To_Change = BeautifulSoup(Where_To_Change, 'html.parser')
                    # Duplicate_Where_To_Change = Where_To_Change
                    # tag = str(Where_To_Change).split("<")[1].split(">")[0]
                    # if " " in tag: tag = tag.split(" ")[0]
                    # if "Replace_Font_With" in request.POST and request.POST['Replace_Font_With'] != "":
                    #     try:
                    #         if(Where_To_Change.find(tag)['style']):
                    #             Change_Text = str(Where_To_Change.find(tag)['style']).replace('\r', '')
                    #             if "font-size" in Change_Text:
                    #                 temp1 = str(Change_Text.split("font-size:")[1].split("px;")[0])
                    #                 temp2 = str(request.POST['Replace_Font_With'])
                    #                 Change_Text = Change_Text.replace(temp1, temp2)
                    #             else:
                    #                 temp1 = str(Change_Text.split(";")[0])
                    #                 temp2 = str(request.POST['Replace_Font_With'])
                    #                 temp2 = temp1 + ";font-size:" + temp2 + "px"
                    #                 Change_Text = Change_Text.replace(temp1, temp2)
                    #             Where_To_Change.find(tag)['style'] = Change_Text
                    #     except:
                    #         temp2 = str(request.POST['Replace_Font_With'])
                    #         Where_To_Change.find(tag)['style'] = f'font-size:{temp2}px;'
                            
                    # if "Replace_Color_With" in request.POST and request.POST['Replace_Color_With'] != "#000000":
                    #     try:
                    #         if(Where_To_Change.find(tag)['style']):
                    #             Change_Text = str(Where_To_Change.find(tag)['style'])
                    #             if "color" in Change_Text:
                    #                 temp1 = str(Change_Text.split("color:")[1].split(";")[0])
                    #                 temp2 = str(request.POST['Replace_Color_With'])
                    #                 Change_Text = Change_Text.replace(temp1, temp2)
                    #             else:
                    #                 temp1 = str(Change_Text.split(";")[0])
                    #                 temp2 = str(request.POST['Replace_Color_With'])
                    #                 temp2 = temp1 + ";color:" + temp2
                    #                 Change_Text = Change_Text.replace(temp1, temp2)
                    #             Where_To_Change.find(tag)['style'] = Change_Text
                    #     except:
                    #         temp2 = str(request.POST['Replace_Color_With'])
                    #         Where_To_Change.find(tag)['style'] = f'color:{temp2};'
                            
                    # New_font = str(Where_To_Change)
                    # soup = str(soup)
                    # if(Old_font in soup): 
                    #     soup = soup.replace(Old_font, New_font)
                        
                    # original_soup = str(original_soup)
                    
                    # if(Old_font in original_soup): 
                    #     original_soup = original_soup.replace(Old_font, New_font)
                        
                    # soup = BeautifulSoup(soup, "html.parser")
                    # original_soup = BeautifulSoup(original_soup, "html.parser")
                    
                    # if Text_To_Replace != '' and Replace_Text_With != '':
                    #     Soup_Changer = Where_To_Change.string.replace(Text_To_Replace, Replace_Text_With)
                        
                    #     # display soup text change
                    #     for x in soup.find_all(tag, text = re.compile(str(Where_To_Change.string.strip()))):
                    #         if str(x) == str(Duplicate_Where_To_Change):
                    #             Changer = x
                    #             break
                    #     # Changer = soup.find(Where_To_Change)
                    #     # Changer = soup.find(text = re.compile(str(Where_To_Change.string.strip())))
                    #     print(f"Changer: {Changer}")
                    #     Changer.string.replace_with(Soup_Changer)
                    #     print(Changer)
                    #     # raise Exception("Intended")
                    #     # original_soup text change
                    #     # Changer2 = original_soup.find_all(tag= '', text = re.compile(str(Where_To_Change.string.strip())))
                    #     # Changer2 = original_soup.find('title style="font-size:18px;color:#b80a0a;"' ,text = re.compile(str(Where_To_Change.string.strip())))
                    #     # Changer2.replace_with(Soup_Changer)
                    #     # Changer2 = original_soup.find(tag=Where_To_Change.parent, text = str(Where_To_Change.string))
                    #     for x in original_soup.find_all(tag, text = re.compile(str(Where_To_Change.string.strip()))):
                    #         if str(x) == str(Duplicate_Where_To_Change):
                    #             Changer2 = x
                    #             break
                    #     Changer2.string.replace_with(Soup_Changer)
                    #     # print(Changer)
                        
                    # with open(Path_To_Search, "w") as fp:
                    #     fp.write(soup)
                    
                    # msg = "Success. Please push the changes"
                    
                    # Response_Table = get_all_web_elements(soup)
                    # Response_Table_Length = len(Response_Table)
                    # save_btn = "undo"
                
                elif 'current_src' in request.POST:
                    
                    with open(Path_To_Search) as fp:
                        original_soup = BeautifulSoup(fp, 'html.parser')
                        
                    width, height = None, None
                        
                    if request.POST['width'] != '':
                        width = int(request.POST['width'])
                        
                    if request.POST['height'] != '':
                        height = int(request.POST['height'])
                    
                    file_exists = False
                    
                    
                    # save image in directory 
                    if request.POST['available_images'] == "select_availaible_image":
                        current_src = request.POST['current_src']
                        name = request.FILES["filename"].name
                        
                        # reading and saving the image in the same directory as current image
                        image_location = f"{REPO_DIR[:REPO_DIR.rfind('All_Repo')]}{current_src[:current_src.rfind('/')+1]}{name}"
                        if not os.path.exists(image_location):
                            try:
                                image = Image.open(io.BytesIO(request.FILES["filename"].file.read()))
                                image.save(image_location)
                                img_list.append(image_location)
                            except:
                                pass

                        else:
                            file_exists = True
                        
                    else:
                        name = request.POST['available_images'].split('/')[-1]
                    
                    msg = "Success. Please push the changes"
                    save_btn = "undo"
                    
                    if file_exists:
                        msg = "File already exists with same name. Please change file name."
                        save_btn = "save"   
                    else:
                        image_to_change = original_soup.find_all('img')[int(request.POST['index'])]
                        new_src = f"{image_to_change['src'][:image_to_change['src'].rfind('/')+1]}{name}"
                        image_to_change['src'] = new_src

                        if width:
                            image_to_change['width'] = width
                        
                        if height:
                            image_to_change['height'] = height
                    
                        with open(Path_To_Search, "w") as fp:
                                fp.write(original_soup.prettify())
                            
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
                        repo.git.stash("save")
                        msg = "Changes successfully restored"
                        save_btn = "save"
                    
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser')
                    tags = ['style']
                    for t in tags:
                        [s.extract() for s in soup(t)]
                    
                    Response_Table = get_all_web_elements(soup)
                    Response_Table_Length = len(Response_Table)
                    
                    
                elif 'push' in request.POST:
                    
                    # Push the changes to the github repository
                    # try:
                    #     repo.git.add(update=True)
                    #     repo.index.commit(Commit_Message)
                    #     origin = repo.remote(name='origin')
                    #     origin.push()
                    #     msg = "Changes have been pushed successfully"
                    # except:
                    #     msg = "Error! Please try again later"
                    try:
                        change_request = ChangeRequest(client_request=client_request, repo=Repo_Name)
                        change_request.save()
                        msg = "Changes have been pushed successfully"
                    except:
                        msg = "Failed to push changes!"
                        
                    # TemplateResponse(request, "accounts/change_request.html", {'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn})
                    
                else:
                    Html_List = []
                    Response_Table = []
                    Response_Table_Length = len(Response_Table)
                
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
                                         'Path_To_Search': Path_To_Search},
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