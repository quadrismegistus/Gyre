from kivy.uix.screenmanager import Screen,ScreenManager
from kivymd.app import MDApp
from kivymd.uix.button import MDFillRoundFlatButton, MDIconButton
from kivymd.uix.toolbar import MDToolbar
from kivymd.uix.screen import MDScreen
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivymd.theming import ThemeManager
from kivy.properties import ObjectProperty,ListProperty
import time,os
from collections import OrderedDict
from functools import partial
from kivy.uix.screenmanager import NoTransition
from kivymd.uix.label import MDLabel
from kivy.uix.widget import Widget
from kivymd.uix.list import OneLineListItem
from kivymd.uix.card import MDCard, MDSeparator
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivymd.uix.list import * #MDList, ILeftBody, IRightBody, ThreeLineAvatarListItem, TwoLineAvatarListItem, BaseListItem, ImageLeftWidget
from kivy.uix.image import Image, AsyncImage
import requests,json
from kivy.storage.jsonstore import JsonStore
from kivy.core.window import Window
from kivy.core.text import LabelBase
import shutil


Window.size = (640, 1136) #(2.65 * 200, 5.45 * 200)

def log(x):
    with open('log.txt','a+') as of:
        of.write(str(x)+'\n')



class MyLayout(MDBoxLayout):
    scr_mngr = ObjectProperty(None)
    post_id = ObjectProperty()

    def change_screen(self, screen, *args):
        self.scr_mngr.current = screen
    
    def view_post(self,post_id):
        self.post_id=post_id
        self.change_screen('view')


class MyBoxLayout(MDBoxLayout): pass
class MyLabel(MDLabel): pass




#### LOGIN







def get_tor_proxy_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {'http':  'socks5://127.0.0.1:9050',
                       'https': 'socks5://127.0.0.1:9050'}
    return session    

def get_tor_python_session():
    from torpy.http.requests import TorRequests
    with TorRequests() as tor_requests:
        with tor_requests.get_session() as s:
            return s


class MainApp(MDApp):
    title = 'Komrade'
    #api = 'http://localhost:5555/api'
    api = 'http://128.232.229.63:5555/api'
    #api = 'http://komrades.net:5555/api'
    logged_in=False
    store = JsonStore('komrade.json')
    login_expiry = 60 * 60 * 24 * 7  # once a week
    #login_expiry = 5 # 5 seconds

    def get_session(self):
        return get_tor_proxy_session()
        #return get_tor_python_session()

    def build(self):
        # bind 
        global app,root
        app = self
        self.root = root = Builder.load_file('root.kv')
        
        # edit logo
        logo=root.ids.toolbar.ids.label_title
        logo.font_name='assets/Strengthen.ttf'
        logo.font_size='58dp'
        logo.pos_hint={'center_y':0.43}
        # icons
        icons=root.ids.toolbar.ids.right_actions.children
        for icon in icons:
            #log(dir(icon))
            #icon.icon='android' #user_font_size='200sp'
            icon.font_size='58dp'
            icon.user_font_size='58dp'
            icon.width='58dp'
            icon.size_hint=(None,None)
            icon.height='58dp'
 
        if not self.is_logged_in():
            self.root.change_screen('login')
        else:
            self.root.post_id=190
            self.root.change_screen('view')
        return self.root

    def is_logged_in(self):
        if self.logged_in: return True
        if not self.store.exists('user'): return False
        if self.store.get('user')['logged_in']:
            if time.time() - self.store.get('user')['logged_in_when'] < self.login_expiry:
                self.logged_in=True
                return True
        return False

    def do_login(self):
        self.logged_in=True
        self.store.put('user',logged_in=True,logged_in_when=time.time())
        self.root.change_screen('feed')


    def login(self,un,pw):
        url = self.api+'/login'

        with self.get_session() as sess:
            #res = requests.post(url, json={'name':un, 'passkey':pw})
            res = sess.post(url, json={'name':un, 'passkey':pw})

            if res.status_code==200:
                self.do_login()
            else:
                self.root.ids.login_status.text=res.text

    def register(self,un,pw):
        url = self.api+'/register'

        with self.get_session() as sess:
            #res = requests.post(url, json={'name':un, 'passkey':pw})
            res = sess.post(url, json={'name':un, 'passkey':pw})
            if res.status_code==200:
                self.do_login()
            else:
                self.root.ids.login_status.text=res.text

    def post(self, content='', img_src=[]):
        log('content: '+str(content))
        log('img_src: '+str(img_src))

        jsond = {'content':str(content)}

        # upload?
        filename=img_src[0] if img_src and os.path.exists(img_src[0]) else ''            
        
        url_upload=self.api+'/upload'
        url_post = self.api+'/post'
        
        server_filename=''
            
        with self.get_session() as sess:
            if filename:
                log(filename)
                self.root.ids.add_post_screen.ids.post_status.text='Uploading file'
                with sess.post(url_upload,files={'file':open(filename,'rb')}) as r1:
                    if r1.status_code==200:
                        rdata1 = r1.json()
                        server_filename = rdata1.get('filename','')
                        if server_filename:
                            self.root.ids.add_post_screen.ids.post_status.text='File uploaded'


            # add post
            self.root.ids.add_post_screen.ids.post_status.text='Creating post'
            jsond={'img_src':server_filename, 'content':content}
            with sess.post(url_post, json=jsond) as r2:
                log('got back from post: ' + r2.text)
                rdata2 = r2.json()
                post_id = rdata2.get('post_id',None)
                if post_id:
                    self.root.ids.add_post_screen.ids.post_status.text='Post created'
                    self.root.view_post(int(post_id))

    def get_post(self,post_id):
        # get json from cache?
        ofn_json = os.path.join('cache','json',str(post_id)+'.json')
        if os.path.exists(ofn_json):
            with open(ofn_json) as f:
                jsond = json.load(f)
        else:
            with self.get_session() as sess:
                with sess.get(self.api+'/post/'+str(post_id)) as r:
                    jsond = r.json()

                    # cache it!
                    with open(ofn_json,'w') as of:
                        json.dump(jsond, of)
        
        return jsond

        
    def get_image(self, img_src):
        # is there an image?
        if not img_src: return 
        # is it cached?
        ofn_image = os.path.join('cache','img',img_src)
        if not os.path.exists(ofn_image):
            # create dir?
            ofn_image_dir = os.path.split(ofn_image)[0]
            if not os.path.exists(ofn_image_dir): os.makedirs(ofn_image_dir)
            log('getting image!')
            with self.get_session() as sess:
                with sess.get(self.api+'/download/'+img_src,stream=True) as r:
                    with open(ofn_image,'wb') as of:
                        shutil.copyfileobj(r.raw, of)
        return ofn_image



if __name__ == '__main__':
    App = MainApp()
    App.run()
