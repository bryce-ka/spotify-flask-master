from flask import Flask, request, redirect, g, render_template, session, jsonify, make_response
from spotify_requests import spotify
import os
SSK = os.urandom(12)
import json

def confidence(value):
    if value == 2:
        return "Low"
    if value > 2 and value < 9:
        return "Medium"
    else:
        return "High"
    
app = Flask(__name__)
app.secret_key = SSK

# ----------------------- AUTH API PROCEDURE -------------------------

@app.route("/auth")
def auth():
    return redirect(spotify.AUTH_URL)


@app.route("/callback/")
def callback():

    auth_token = request.args['code']
    auth_header = spotify.authorize(auth_token)
    session['auth_header'] = auth_header
    personal_recs = get_recs()
    return make_response(
        personal_recs, 
        200, 
    )


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
        
        
        # get user data- tracks and artists
        artist_dict = {}
        for track_term in ["short_term", "medium_term"]:
            artists = spotify.get_users_top(auth_header,'artists',  track_term, str(num_items))
            for artist in artists['items']:
                if artist['id'] not in  artist_dict.keys():
                    artist_dict[artist['id']]= [artist['name'], 1, artist['popularity']]
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
        
        recs = {}
        easy_list = []
        recommended_artists = {'ids' :{}}
        for key, val in artist_dict.items():
            if val[1] != 1:
                conf_level = confidence(val[1])
                recs[key] = val
                #geting related artists for recs
                related_artists = spotify.get_related_artists(auth_header, key)
                for related in related_artists['artists']:
                    if related['id'] not in recommended_artists['ids'].keys():
                        recommended_artists['ids'][related['id']]={"id": related['id'], "name": related['name'], "popularity": related['popularity'], "confidence": conf_level, "genres": related['genres'], "link": related['uri']}
                        easy_list.append((related['id'], related['popularity']))
                        #need to make links functional 
                        
        #determine reccommendations- done and i think theyre good!
        
        #orders based on popularity 
        easy_list.sort(key=lambda a: a[1], reverse = True)
        
        # for index in range(len(easy_list)):
        #     new_id = (recommended_artists['ids'][easy_list[index][0]]['name'], easy_list[index][1])
        #     easy_list[index] = new_id
        # print(easy_list) #human readable list
        
        final_recs = {'recommendations':{}}
        for artist in easy_list:
            final_recs['recommendations'][artist[1]]= recommended_artists['ids'][artist[0]]
            
         
        # print(easy_list)
        return jsonify(final_recs)
        
    else:
        return "Error: No access token provided. Please login through E-AI."
        

if __name__ == "__main__":
    app.run(debug = True, port=spotify.PORT, threaded=True)
