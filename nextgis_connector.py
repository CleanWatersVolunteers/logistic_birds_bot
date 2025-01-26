from datetime import datetime
import pytz
import requests
import re
import json

time_tz = lambda tz: datetime.utcnow().astimezone(pytz.timezone(tz))
curr_time = lambda : time_tz('Etc/GMT-6').isoformat().split('+')[0]

ngw_host = 'https://blacksea-monitoring.nextgis.com'
f_lgn = open('nextgis_login', 'r')
f_pass = open('nextgis_pass', 'r')

auth = (f_lgn.read(),f_pass.read())

f_lgn.close()
f_pass.close()

class NextGIS:
    ngw_host = 'https://blacksea-monitoring.nextgis.com'
    url_feature = ngw_host + '/api/resource/' + str(195) +'/feature/'

    @classmethod
    def _get(cls, url):
        print("[..] GET:",url)
        response = requests.get(url, auth=cls.__auth)
        if response.status_code != 200:
            print("[!!] GET code", response.status_code, response.text)
            return response.status_code, {}
        return response.status_code, response.json()
    @classmethod
    def _post(cls, url, data):
        print("[..] POST:",url)
        if data:
            response = requests.post(url, auth=cls.__auth,data=json.dumps(data))
        else:
            response = requests.post(url, auth=cls.__auth, data=None)
        if response.status_code != 200:
            print("[!!] POST code", response.status_code, response.text)
            return response.status_code, {}
        return response.status_code, response.json()
    @classmethod
    def _put(cls, url, data):
        print("[..] PUT:",url)
        if data:
            response = requests.put(url, auth=cls.__auth,data=json.dumps(data))
        else:
            response = requests.put(url, auth=cls.__auth, data=None)
        if response.status_code != 200:
            print("[!!] PUT code", response.status_code, response.text)
            return response.status_code, {}
        return response.status_code, response.json()
    @classmethod
    def _get_flt(cls, features)->{}:
        req = "?"
        for key in features:
           req += f'{key}={features[key]}&'
        req = req[:-1]
        code, resp = cls._get(cls.url_feature+req)
        if code == 200:
            return resp
        return {}

    @classmethod
    def init(cls)->bool:
        cls.__db = dict()
        try:
            # Auth 

            f_lgn = open('nextgis_login', 'r')
            f_pass = open('nextgis_pass', 'r')
            cls.__auth = (f_lgn.read(),f_pass.read())
            f_lgn.close()
            f_pass.close()

            # create local base

            code, resp = cls._get(cls.url_feature)
            if code != 200:
                return False
            for item in resp:
                contact_link = item['fields']['contact_info']
                if contact_link:
                    link = re.search("https://t.me/",contact_link)
                    if link:
                        cls.__db[contact_link[link.span()[1]:]] = item['id']
        except Exception as e:
            print("[!!] GextGIS Init exeption!", e)
            return False
        return True

    @classmethod
    def get_id(cls,name)->int:
        if name in cls.__db:
            return cls.__db[name]
        return 0
    @classmethod
    def get_name(cls,id)->str:
        for key in cls.__db:
            if cls.__db[key] == id:
                return key
        return None
    @classmethod
    def get_free_list(cls,who)->{}:
        features = cls._get_flt({"fld_end_route":"выполняется", "fld_status":who})
        if features:
            return features
        return {}

    @classmethod
    def new_user(cls,name)->{}:
        if not name:
            return {}
        print("[..] Add new user", name)
        feature = dict()
        feature['extensions'] = dict()
        feature['extensions']['attachment'] = None
        feature['extensions']['description'] = None
        feature['fields'] = dict()
        feature['fields']['contact_info'] = f"https://t.me/{name}"
        code, data = cls._post(cls.url_feature+"?srs=4326&dt_format=iso", feature)
        if code == 200:
            if 'id' in data:
                cls.__db[name] = data['id']
                return cls.get_user(name)
        return {}

    @classmethod
    def get_user(cls,name)->{}:
        if not name in cls.__db:
            return {}
        id = cls.__db[name]
        # code, res = cls._get(cls.url_feature+f"{id}?srs=4326&dt_format=iso")
        code, res = cls._get(cls.url_feature+f"{id}?srs=4326")
        if code != 200:
            return {}
        return res['fields']

    # GEO: long,lat
    # STATUS: car,cargo_type,status,end_route  
    @classmethod
    def upd_user(cls,name, details)->bool:
        id = cls.get_id(name)
        if id == 0:
            return False

        # main data
        feature = dict()
        feature['fields'] = dict()
        for key in details:
            feature['fields'][key] = details[key]
        
        # time 
        time = curr_time()
        feature['fields']['dt_auto'] = time
        if "long" in details and "lat" in details:
            feature['fields']['dt_coord'] = time 
            feature['geom'] = 'POINT (%s %s)' % (details["long"], details["lat"])
        if "status" in details or "end_route" in details:
            feature['fields']['dt_data'] = time 

        # Request
        put_url = f"{cls.url_feature}{id}?srs=4326&dt_format=iso"
        code,_ = cls._put(put_url, feature)
        if code == 200:
            return True
        return False

    @classmethod
    def complete_user(cls,name):
        cls.upd_user(name, {"long":0, "lat":0,"end_route":"завершено"})

