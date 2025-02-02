from datetime import datetime, timedelta
import pytz
import requests
import re
import json
import os
import math

time_tz = lambda tz: datetime.now(pytz.timezone(tz))
curr_time = lambda : time_tz('Etc/GMT-3').isoformat().split('+')[0]


ngw_host = 'https://blacksea-monitoring.nextgis.com'
                                  
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
    def _calc_dist(cls, user_lat, user_lon, search_lat, search_lon):
    #здесь:
    # search_lat, search_lon - искомая точка на местности
    # user_lat, user_lon - точка текущего пользователя
    # dist - рассчитанное расстояние
        r = 6373.0  # radius of the Earth
        # coordinates in radians
        lat1 = math.radians(float(search_lat))
        lon1 = math.radians(float(search_lon))
        lat2 = math.radians(float(user_lat))
        lon2 = math.radians(float(user_lon))
        # change in coordinates
        d_lon = lon2 - lon1
        d_lat = lat2 - lat1
        # Haversine formula
        a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = r * c
        dist = round(distance)

        return dist
    
    
    @classmethod
    def _get_flt(cls, feature_conditions)->{}:
        req = "?"
        # https://blacksea-monitoring.nextgis.com/api/resource/100/feature/?fld_dt_auto__le=2025-01-15T00:00:00&dt_format=iso
                                         
        for feature_condition in feature_conditions:
           req += f'{feature_condition}&'
        req = req[:-1]
        code, resp = cls._get(cls.url_feature+req)
        return resp if code == 200 else {}

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
            cls.__auth = (f_lgn,f_pass)

            
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
    def get_free_list(cls,who, user, max_distance_limit)->{}:
        features = cls._get_flt(["fld_end_route=выполняется", f"fld_status={who}"])
        for i, feature in enumerate(features):
            dist = cls._calc_dist(user["lat"], user["long"], feature["fields"]["lat"], feature["fields"]["long"] )
            feature["dist"] = dist

        for i, feature in enumerate(features):
            if max_distance_limit>0 and feature["dist"] > max_distance_limit:
                features.pop(i)
        return features if features else {}

    @classmethod
    def get_old_list(cls)->{}:
        old_time = (datetime.fromisoformat(curr_time()) - timedelta(hours=12)).isoformat().split('+')[0]
        old_time = datetime.fromisoformat(old_time)
        time_condition = f"{old_time.year}-{old_time.month:02}-{old_time.day:02}T{old_time.hour:02}:{old_time.minute:02}:{old_time.second:02}"
        time_condition = f"fld_dt_auto__le={time_condition}"
        # https://blacksea-monitoring.nextgis.com/api/resource/100/feature/?fld_dt_auto__le=2025-01-15T00:00:00&dt_format=iso
        
        features = cls._get_flt([time_condition, "dt_format=iso"])
        return features if features else {}
    
    @classmethod
    def new_user(cls,name)->{}:
        print("[..] Add new user", name)
        if not name:
            return {}
                                        
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

