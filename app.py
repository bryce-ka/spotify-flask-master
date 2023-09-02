from flask import Flask, request, redirect, g, render_template, session, jsonify, make_response
from spotify_requests import spotify
import os
import pandas as pd
SSK = os.urandom(12)
import json
artist_dict = {}

def confidence(value):
    if value == 2:
        return "Medium"
    if value > 2 and value < 9:
        return "High"
    else:
        return "Very high"
    
app = Flask(__name__)
app.secret_key = SSK

# ----------------------- AUTH API PROCEDURE -------------------------

# @app.route("/auth")
# def auth():
#     return redirect(spotify.AUTH_URL)


# @app.route("/callback/")
# def callback():

#     auth_token = request.args['code']
#     auth_header = spotify.authorize(auth_token)
#     session['auth_header'] = auth_header
#     personal_recs = get_recs()
#     return make_response(
#         personal_recs, 
#         200, 
#     )


def valid_token(resp):
    return resp is not None and not 'error' in resp

# -------------------------- API REQUESTS ----------------------------


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/tut", methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/get_you')
def you():

    if 'token' in request.args:
        access_token = request.args['token']
        auth_header = {"Authorization": "Bearer {}".format(access_token)}
         # get specifications 
        # query= str(request.args.get)
        term_len = "long_term"
        num_items = 50
        
        
        # get user data- tracks and artists
        need_images = []
        artist_dict = {}
        for track_term in ["short_term", "medium_term"]:
            artists = spotify.get_users_top(auth_header,'artists',  track_term, str(num_items))
            for artist in artists['items']:
                if artist['id'] not in  artist_dict.keys():
                    artist_dict[artist['id']]= [artist['name'], 1, artist['popularity'], artist['images'][1]['url']]
                   
                else:
                    artist_info = artist_dict[artist['id']] 
                    artist_info[1] += 1
                    artist_dict[artist['id']] = artist_info
      
        for track_term in ["short_term", "medium_term"]:
            tracks = spotify.get_users_top(auth_header,'tracks', track_term, str(num_items))
            for track in tracks['items']:
                for each_artist in track['artists']:
                    if each_artist['id'] not in  artist_dict.keys():
                        artist_dict[each_artist['id']]= [each_artist['name'], 1, -1]
                        
                        
                    else:
                        artist_info = artist_dict[each_artist['id']] 
                        artist_info[1] += 1
                        artist_dict[each_artist['id']] = artist_info
            
        your_artists = {'ids' :{}}
        for key, val in artist_dict.items():
            if val[1] != 1:
                conf_level = confidence(val[1])
                try:
                    your_artists['ids'][key]={"id": key, "name": val[0], "interest": conf_level, "image": val[3]}
                except:
                    need_images.append(key)
                    your_artists['ids'][key]={"id": key, "name": val[0], "interest": conf_level}

        while len(need_images) != 0:
            if len(need_images) > 50:
                num_ids=50 #max of call
                num_ids-=1 #indexing 
            else:
                num_ids= len(need_images)
                num_ids-=1
                
            artist_infos = spotify.get_several_artists(auth_header, need_images[0:num_ids])
            
            for id in range(len(need_images[0:num_ids])):
                
                if id == 0:
                    print(need_images[id])
                    
                temp = your_artists['ids'][need_images[id]]
                temp_id = need_images[id]
                temp_name = temp['name']
                temp_interest = temp['interest']
                temp_image = artist_infos['artists'][id]['images'][1]['url']
                your_artists['ids'][temp_id]= {"id": temp_id, "name": temp_name, "interest": temp_interest, "image": temp_image}
            need_images = need_images[num_ids+1:]
            # print(your_artists['ids'])
        
        # return redirect(
        # 'http://127.0.0.1:5000/recs?token=' + access_token,
        # 302,
        # jsonify(your_artists))
        return jsonify(your_artists)
        
    else:
        return "Error: No access token provided. Please login through E-AI."
    
    
    

@app.route('/recs', methods=['GET'])
def get_recs():
    
    """
    recommends artists based on recent listening habits, *can adjust the popularity*
    """
    #take acess token and send to spotify.py 
    if 'token' in request.args:
        access_token = request.args['token']
        auth_header = {"Authorization": "Bearer {}".format(access_token)}
         # get specifications 
        # query= str(request.args.get)
        term_len = "long_term"
        num_items = 50
        #dictionary with potential artist recomendations 
        ea_dict = {}
        easy_list = []

        user_preferences = you()
        # get user preferences/interests
        
        user_preferences = json.loads(user_preferences.get_data())
        #create a table  of the artists in user_preferences and their info then save it as an htmnl file
        html = pd.DataFrame.from_dict(user_preferences['ids'], orient='index') 
        html = html.sort_values(by=['interest'])
        html = html.to_html()
        #save the html to a file
        text_file = open("templates/user_preferences.html", "w")
        text_file.write(html)
        text_file.close()


        #use the spotify api to get related artists for each artist in the user_preferences dictionary and add related artists and their info to a dict called rec_dict
        for key, val in user_preferences['ids'].items():
            related_artists = spotify.get_related_artists(auth_header, key)
            for related in related_artists['artists']:
                if related['id'] not in user_preferences['ids'].keys():
                    if related['id'] not in ea_dict.keys():
                        ea_dict[related['id']]= {"name": related['name'], "freq": 1, "popularity": related['popularity'], "genres": related['genres'], "link": related['uri']}
                    else:
                        artist_info = ea_dict[related['id']] 
                        artist_info['freq'] += 1
                        ea_dict[related['id']] = artist_info
        

        #create a table  of the artists in ea_dict and their info
        recommended_artists = {'ids' :{}}
        for key, val in ea_dict.items():
            if val['freq'] != 1:
                conf_level = confidence(val['freq'])
                recommended_artists['ids'][key]={"id": key, "name": val['name'], "interest": conf_level, "popularity": val['popularity'], "genres": val['genres'], "link": val['link']}
        
        #format it as html to be displayed in a browser
        html = pd.DataFrame.from_dict(recommended_artists['ids'], orient='index')
        html = html.sort_values(by=['interest', 'popularity'])
        #save the html to a file
        html = html.to_html()
        text_file = open("templates/recommended_artists.html", "w")
        text_file.write(html)
        text_file.close()

        #convert recommended artists to a json object and return it
        return jsonify(recommended_artists)
        
    else:
        return "Error: No access token provided. Please login through E-AI."
        

if __name__ == "__main__":
    app.run(debug = True, port=spotify.PORT, threaded=True)
