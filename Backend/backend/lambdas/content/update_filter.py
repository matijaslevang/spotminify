import boto3
import json
import os
from typing import Set

dynamodb = boto3.resource('dynamodb')
genre_index_table = dynamodb.Table(os.environ['GENRE_INDEX_TABLE'])
artist_index_table = dynamodb.Table(os.environ['ARTIST_INDEX_TABLE'])

def handler(event, context):
    """
    Rukuje ažuriranjem index tabela (žanrovi i izvođači) za SINGLE ili ALBUM.
    Prima staro i novo stanje sadržaja.
    """
    try:
        body = event
        
        content_id = body.get('contentId')
        content_type = body.get('contentType')
        old_content = body.get('oldContent', {})
        new_content = body.get('newContent', {})
        
        if content_type not in ['single', 'album']:
            print(f"Nepodržani contentType za ažuriranje filtera: {content_type}")
            return {'statusCode': 200, 'body': 'Ignored'}

        content_key = f"{content_type}-{content_id}"

        # 1. AŽURIRANJE ŽANROVA (GENRE_INDEX)
        
        old_genres: Set[str] = set(old_content.get('genres', []))
        new_genres: Set[str] = set(new_content.get('genres', []))
        
        genres_to_add: Set[str] = new_genres - old_genres # Novi žanrovi
        genres_to_remove: Set[str] = old_genres - new_genres # Žanrovi za brisanje
        genres_to_keep: Set[str] = old_genres.intersection(new_genres) # Žanrovi koji ostaju isti
        
        print(f"Žanrovi za dodavanje: {genres_to_add}, Žanrovi za brisanje: {genres_to_remove}, Žanrovi za zadržavanje: {genres_to_keep}")
        # Brisanje starih unosa
        for genre in genres_to_remove:
            try:
                genre_index_table.delete_item(
                    Key={'genreName': genre, 'contentKey': content_key}
                )
            except Exception as e:
                print(f"Greška pri brisanju starog genre indexa ({genre}): {str(e)}")

        # Dodavanje novih unosa
        new_item = {
            'contentKey': content_key,
            'contentId': content_id,
            'contentType': content_type,
            'content': new_content,
        }
        for genre in genres_to_add:
            add_item = new_item.copy()
            add_item['genreName'] = genre
            genre_index_table.put_item(Item=add_item)


        # 2. AŽURIRANJE IZVOĐAČA (ARTIST_INDEX)

        # Uzimamo Artist ID-jeve
        old_artists: Set[str] = set(old_content.get('artistIds', []))
        new_artists: Set[str] = set(new_content.get('artistIds', []))
        
        artists_to_add: Set[str] = new_artists - old_artists
        artists_to_remove: Set[str] = old_artists - new_artists
        
        print(f"Izvođači za dodavanje: {artists_to_add}, Izvođači za brisanje: {artists_to_remove}")

        # Brisanje starih unosa
        for artist_id in artists_to_remove:
            try:
                artist_index_table.delete_item(
                    Key={'artistId': artist_id, 'contentKey': content_key}
                )
            except Exception as e:
                print(f"Greška pri brisanju starog artist indexa ({artist_id}): {str(e)}")

        # Dodavanje novih unosa
        for artist_id in artists_to_add:
            add_item = new_item.copy()
            add_item['artistId'] = artist_id
            artist_index_table.put_item(Item=add_item)

        return {'statusCode': 200, 'body': json.dumps({'message': 'Filter indexes updated successfully'})}

    except Exception as e:
        print(f"Generalna greška u update_filter: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
