from datetime import datetime
import pytz
import requests
import json

# time_tz = lambda tz: datetime.now(pytz.timezone(tz))
# curr_time = lambda : time_tz('Etc/GMT+6')

time_tz = lambda tz: datetime.utcnow().astimezone(pytz.timezone(tz))
curr_time = lambda : time_tz('Etc/GMT-3').isoformat().split('+')[0]

ngw_host = 'https://blacksea-monitoring.nextgis.com'
f_lgn = open('nextgis_login', 'r')
f_pass = open('nextgis_pass', 'r')

auth = (f_lgn.read(),f_pass.read())

f_lgn.close()
f_pass.close()

def create_request_fields(lat,lon,car=None,status=None,cargo_type=None,end_route=None)->dict:
    feature = dict()
    feature['fields'] = dict()
    feature['fields']['lat'] = lat
    feature['fields']['long'] = lon
    if car != None:
        feature['fields']['car'] = car
    if cargo_type != None:
        feature['fields']['cargo_type'] = cargo_type
    if status != None:
        feature['fields']['status'] = status
    if end_route != None:
        feature['fields']['end_route'] = end_route
    feature['fields']['dt_auto'] = curr_time()
    return feature

def add_point_track(tg_link)->int:
    print("[..] Add point to",tg_link)

    feature = dict()
    feature['extensions'] = dict()
    feature['extensions']['attachment'] = None
    feature['extensions']['description'] = None
    feature['fields'] = dict()
    feature['fields']['contact_info'] = f"https://t.me/{tg_link}"

    post_url = ngw_host + '/api/resource/' + str(195) +'/feature/?srs=4326&dt_format=iso'
    print(feature, post_url)
    response = requests.post(post_url, data=json.dumps(feature), auth=auth)
    
    if response.status_code == 200:
        print("Feature created successfully:", response.json())
        return response.json()['id']
    else:
        print("Error creating feature:", response.status_code, response.text)
        return 0

def update_details(point_id, car, cargo_type, status, comment):
    print("[..] Update details", point_id, car, status,comment)

    feature = create_request_fields(lat=0,lon=0,car=car,cargo_type=cargo_type, status=status)
    feature['fields']['dt_data'] = curr_time()

    put_url = f"{ngw_host}/api/resource/{195}/feature/{point_id}?srs=4326&dt_format=iso"
    print(feature, put_url)
    response = requests.put(put_url, data=json.dumps(feature), auth=auth)
    if response.status_code != 200:
        print("Error creating feature:", response.status_code, response.text)


def move_point_track(point_id, lat, lon, end_route):
    print("[..] Modify point", point_id,lat,lon, end_route)

    feature = create_request_fields(lat=lat,lon=lon,end_route=end_route)
    feature['fields']['dt_coord'] = curr_time()
    feature['geom'] = 'POINT (%s %s)' % (lon, lat)

    put_url = f"{ngw_host}/api/resource/{195}/feature/{point_id}?srs=4326&dt_format=iso"
    print(feature, put_url)
    response = requests.put(put_url, data=json.dumps(feature), auth=auth)
    # print(response)
    if response.status_code != 200:
        print("Error creating feature:", response.status_code, response.text)
