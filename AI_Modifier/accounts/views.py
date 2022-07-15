import git
import os
from bs4 import BeautifulSoup
import re

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

from accounts.models import ClientRequest, ChangeRequest
from modifier_admin.models import Profile



def index(request):   
    
    context = {}
    
    if request.user.is_authenticated:
        print(f'from: {request.user.email}')
        try:
            context['message'] = 'Welcome to AI Modifier'
            profile = Profile.objects.get(email=request.user.email)        
            context['user'] = request.user
            if len(profile.client_request.all()) > 0 :
                context['urls'] = [client_req.url for client_req in profile.client_request.all()]
            
            return TemplateResponse(request, 'accounts/index.html', context)
        except Exception as e:
            print('No user found')
         
    return TemplateResponse(request, 'accounts/index.html', {'message': 'Please login to continue.'})



def signin(request):

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(email=email, password=password)

        try:
            login(request, user)
            return HttpResponseRedirect(reverse('index'))
            
            
        except Exception as e:
            print(f'Exception: {e}')
            return TemplateResponse(request, 'accounts/signin.html', {'message':'Invalid Credentials'})
        
    return TemplateResponse(request, 'accounts/signin.html')

def add_request(request):
    
    if request.method == 'POST':
        
        try:
            if ClientRequest.objects.filter(url=request.POST['url']).exists():
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
                instance = ClientRequest(url=request.POST['url'],
                                        code_link=request.POST['link'],
                                        username=request.POST['username'],
                                        token=request.POST['token'],
                                        version_control=request.POST['version_control'],
                                        branch=request.POST['branch'],
                                        profile=Profile.objects.get(email=request.POST['email']))
                instance.save()
            
            return HttpResponseRedirect(reverse('index'))
        except Exception as e:
            print(f'Some exception occurred: {e}')
            return TemplateResponse(request, 'accounts/add_request.html', {'message': 'Could not add request. Try Again!'})
            
    return TemplateResponse(request, 'accounts/add_request.html', {'message': 'Add new request'})

def change_request(request):
    
    if request.method == 'POST':
        try:
            client_request = ClientRequest.objects.get(url=request.POST['client_req_urls'])
            
            url = client_request.url
            code_link = client_request.code_link
            username = client_request.username
            token = client_request.token
            version_control = client_request.version_control
            branch = client_request.branch
            profile = client_request.profile
            
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
                global Repo_Path
                global Repo_Name
                global Branch_Name
                global Text_To_Replace
                global Path_To_Search
                global Response_Table
                global Response_Table_Length
                global original_soup
                global soup
                global repo
                global save_btn
                global content_btn
                global Html_List
                msg = ""
                save_btn = "save"
                content_btn = "text"
                Html_List = []
                Response_Table = []
                Response_Table_Length = len(Response_Table)
                Repo_Path = f"{code_link[:code_link.find('//')+2]}{username}:{token}@{code_link[code_link.find('//')+2:]}"
                print(f'Repo: {Repo_Path}')
                Branch_Name = branch
                Repo_Name = "All_Repo/" + Repo_Path[Repo_Path.rfind('/')+1:].split('.')[0]
                
                Html_List = []
                for root, dirnames, filenames in os.walk(Repo_Name):
                    for filename in filenames:
                        if filename.endswith('.html'):
                            Html_List.append(os.path.join(root, filename))
                
                # if 'Repo_Path' in request.POST and 'Branch_Name' in request.POST and 'Page_Name' not in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                if 'make_changes' in request.POST:
                    # Repo_Path = request.POST['Repo_Path']
                    # Branch_Name = request.POST['Branch_Name']
                    # Repo_Name = "All_Repo/" + Repo_Path[Repo_Path.rfind('/')+1:].split('.')[0]
                    
                    # Auto pull remote repository and change branch
                    if not(os.path.exists("All_Repo")):
                        os.mkdir("All_Repo")

                    if not(os.path.exists(Repo_Name)):
                        repo = git.Repo.clone_from(Repo_Path, Repo_Name)
                    else:
                        repo = git.Repo(Repo_Name)
                        repo.git.reset("--hard")
                        
                    repo.git.checkout(Branch_Name)
                    # repo.git.pull()
                    
                    # Pull all the HTML files available in the repository
                    
                    
                    # TemplateResponse(request, "accounts/change_request.html", {'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn})
                
                elif 'Page_Name' in request.POST and 'save' not in request.POST and 'push' not in request.POST:
                    
                    # Pull all the Editable content from the HTML page
                    Path_To_Search = request.POST['Page_Name']
                    with open(Path_To_Search) as fp:
                        soup = BeautifulSoup(fp, 'html.parser')
                        # tags = ['style', 'script', 'head', 'title', 'meta', '[document]']
                        tags = ['style']
                        for t in tags:
                            [s.extract() for s in soup(t)]
                        Response_Table = []
                        for x in soup.find_all(tag='', text=re.compile('')):
                            tag = str(x).split("<")[1].split(">")[0]
                            if " " in tag: tag = tag.split(" ")[0]
                            soup_string = str(x.string)
                            if "{{" in soup_string and "}}" in soup_string: continue
                            text = str(x)
                            if text.find("font-size") != -1:
                                size = str(text.split("font-size:")[1].split("px;")[0])
                            else:
                                size = ""
                            if text.find("color") != -1:
                                color = text.split("color:")[1].split(";")[0]
                            else:
                                color = ""
                            temp = [tag, soup_string, text ,size, color]
                            Response_Table.append(temp)
                        temp = []
                        for x in Response_Table:
                            if x not in temp:
                                temp.append(x)
                        Response_Table = temp
                        Response_Table_Length = len(Response_Table)
                    # TemplateResponse(request, "accounts/change_request.html", {'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn})
                    
                elif 'Replace_Text_With' in request.POST and 'Text_To_Replace' in request.POST and 'Where_To_Change' in request.POST:
                    
                    # Replace the text in the soup
                    save_btn = "save"
                    with open(Path_To_Search) as fp:
                        original_soup = BeautifulSoup(fp, 'html.parser')
                    Where_To_Change = request.POST['Where_To_Change'].replace('\r', '')
                    Old_font = str(Where_To_Change)
                    Text_To_Replace = request.POST['Text_To_Replace']
                    Replace_Text_With = request.POST['Replace_Text_With']
                    Where_To_Change = BeautifulSoup(Where_To_Change, 'html.parser')
                    Duplicate_Where_To_Change = Where_To_Change
                    tag = str(Where_To_Change).split("<")[1].split(">")[0]
                    if " " in tag: tag = tag.split(" ")[0]
                    if "Replace_Font_With" in request.POST and request.POST['Replace_Font_With'] != "":
                        try:
                            if(Where_To_Change.find(tag)['style']):
                                Change_Text = str(Where_To_Change.find(tag)['style']).replace('\r', '')
                                if "font-size" in Change_Text:
                                    temp1 = str(Change_Text.split("font-size:")[1].split("px;")[0])
                                    temp2 = str(request.POST['Replace_Font_With'])
                                    Change_Text = Change_Text.replace(temp1, temp2)
                                else:
                                    temp1 = str(Change_Text.split(";")[0])
                                    temp2 = str(request.POST['Replace_Font_With'])
                                    temp2 = temp1 + ";font-size:" + temp2 + "px"
                                    Change_Text = Change_Text.replace(temp1, temp2)
                                Where_To_Change.find(tag)['style'] = Change_Text
                        except:
                            temp2 = str(request.POST['Replace_Font_With'])
                            Where_To_Change.find(tag)['style'] = f'font-size:{temp2}px;'
                            
                    if "Replace_Color_With" in request.POST and request.POST['Replace_Color_With'] != "#000000":
                        try:
                            if(Where_To_Change.find(tag)['style']):
                                Change_Text = str(Where_To_Change.find(tag)['style'])
                                if "color" in Change_Text:
                                    temp1 = str(Change_Text.split("color:")[1].split(";")[0])
                                    temp2 = str(request.POST['Replace_Color_With'])
                                    Change_Text = Change_Text.replace(temp1, temp2)
                                else:
                                    temp1 = str(Change_Text.split(";")[0])
                                    temp2 = str(request.POST['Replace_Color_With'])
                                    temp2 = temp1 + ";color:" + temp2
                                    Change_Text = Change_Text.replace(temp1, temp2)
                                Where_To_Change.find(tag)['style'] = Change_Text
                        except:
                            temp2 = str(request.POST['Replace_Color_With'])
                            Where_To_Change.find(tag)['style'] = f'color:{temp2};'
                            
                    New_font = str(Where_To_Change)
                    soup = str(soup)
                    if(Old_font in soup): soup = soup.replace(Old_font, New_font)
                    original_soup = str(original_soup)
                    if(Old_font in original_soup): original_soup = original_soup.replace(Old_font, New_font)
                    soup = BeautifulSoup(soup, "html.parser")
                    original_soup = BeautifulSoup(original_soup, "html.parser")
                    
                    if Text_To_Replace != '' and Replace_Text_With != '':
                        Soup_Changer = Where_To_Change.string.replace(Text_To_Replace, Replace_Text_With)
                        
                        # display soup text change
                        for x in soup.find_all(tag, text = re.compile(str(Where_To_Change.string.strip()))):
                            if str(x) == str(Duplicate_Where_To_Change):
                                Changer = x
                                break
                        # Changer = soup.find(Where_To_Change)
                        # Changer = soup.find(text = re.compile(str(Where_To_Change.string.strip())))
                        print(f"Changer: {Changer}")
                        Changer.string.replace_with(Soup_Changer)
                        print(Changer)
                        # raise Exception("Intended")
                        # original_soup text change
                        # Changer2 = original_soup.find_all(tag= '', text = re.compile(str(Where_To_Change.string.strip())))
                        # Changer2 = original_soup.find('title style="font-size:18px;color:#b80a0a;"' ,text = re.compile(str(Where_To_Change.string.strip())))
                        # Changer2.replace_with(Soup_Changer)
                        # Changer2 = original_soup.find(tag=Where_To_Change.parent, text = str(Where_To_Change.string))
                        for x in original_soup.find_all(tag, text = re.compile(str(Where_To_Change.string.strip()))):
                            if str(x) == str(Duplicate_Where_To_Change).replace('\r', ''):
                                Changer2 = x
                                break
                        Changer2.string.replace_with(Soup_Changer)
                        # print(Changer)
                    
                    msg = "Success. Please save the changes"
                    
                    Response_Table = []
                    for x in soup.find_all(tag='', text=re.compile('')):
                        tag = str(x).split("<")[1].split(">")[0]
                        if " " in tag: tag = tag.split(" ")[0]
                        soup_string = str(x.string)
                        if "{{" in soup_string and "}}" in soup_string: continue
                        text = str(x)
                        if text.find("font-size") != -1:
                            size = str(text.split("font-size:")[1].split("px;")[0])
                        else:
                            size = ""
                        if text.find("color") != -1:
                            color = text.split("color:")[1].split(";")[0]
                        else:
                            color = ""
                        temp = [tag, soup_string, text ,size, color]
                        Response_Table.append(temp)
                    temp = []
                    for x in Response_Table:
                        if x not in temp:
                            temp.append(x)
                    Response_Table = temp
                    Response_Table_Length = len(Response_Table)
                    # TemplateResponse(request, "accounts/change_request.html", {'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn})
                    
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
                    Response_Table = []
                    for x in soup.find_all(tag='', text=re.compile('')):
                        tag = str(x).split("<")[1].split(">")[0]
                        if " " in tag: tag = tag.split(" ")[0]
                        soup_string = str(x.string)
                        if "{{" in soup_string and "}}" in soup_string: continue
                        text = str(x)
                        if text.find("font-size") != -1:
                            size = str(text.split("font-size:")[1].split("px;")[0])
                        else:
                            size = ""
                        if text.find("color") != -1:
                            color = text.split("color:")[1].split(";")[0]
                        else:
                            color = ""
                        temp = [tag, soup_string, text ,size, color]
                        Response_Table.append(temp)
                    temp = []
                    for x in Response_Table:
                        if x not in temp:
                            temp.append(x)
                    Response_Table = temp
                    Response_Table_Length = len(Response_Table)
                    # TemplateResponse(request, "accounts/change_request.html", {'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn})
                    
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
                
                # print(f'Response Table: {Response_Table}')
                return TemplateResponse(request, "accounts/change_request.html", {'user':profile, 'repo':code_link, 'branch':branch, 'Html_List':Html_List, 'Table':Response_Table, 'Table_Length':Response_Table_Length, 'msg':msg, 'save_btn':save_btn, 'client_req_urls':request.POST['client_req_urls']})
            
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