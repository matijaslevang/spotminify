import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { Album, Artist, Genre, Song } from './models/model';
import { environment } from '../../enviroment';

@Injectable({
  providedIn: 'root'
})
export class ContentService {
  // Mock subscriptions
  private _mySubscriptions = new Set<string>();
  constructor(private httpClient: HttpClient) { }

  getArtist(artistId: string): Observable<Artist> {
    return this.httpClient.get<Artist>(`${environment.apiUrl}/get-artist`, {
      params: { artistId: artistId }
    })
  }
  
  getArtists(): Observable<Artist[]> {
    return this.httpClient.get<Artist[]>(`${environment.apiUrl}/artists-all`)
  }

  deleteSingle(singleId: string): Observable<any> {
    return this.httpClient.delete(`${environment.apiUrl}/singles/${singleId}`);
   }
  
   deleteAlbum(albumId: string): Observable<any> {
    return this.httpClient.delete(`${environment.apiUrl}/albums/${albumId}`);
  }

  deleteArtist(artistId: string): Observable<any> {
      return this.httpClient.delete(`${environment.apiUrl}/artists/${artistId}`);
  }

  getSongsByArtist(artistName: string): Observable<Song[]> {
    return of(null) // TODO
  }

  getAlbumsByArtist(artistName: string): Observable<Album[]> {
    return of(null) // TODO
  }

  getSong(singleId: string): Observable<Song> {
    return this.httpClient.get<Song>(`${environment.apiUrl}/get-single`, {
      params: { singleId: singleId }
    })
  }

  getAlbum(albumId: string): Observable<Album> {
    return this.httpClient.get<Album>(`${environment.apiUrl}/get-album`, {
      params: { albumId: albumId }
    })
  }

  getSongsByAlbum(albumId: string): Observable<Song[]> {
    return this.httpClient.get<Song[]>(`${environment.apiUrl}/get-album-songs`, {
      params: { albumId: albumId }
    })
  }

  getRecommendedFeed(): Observable<any> {
    return this.httpClient.get(`${environment.apiUrl}/feed`)
  }
  updateArtist(fd: FormData){ return this.httpClient.put(`${environment.apiUrl}/artists`, fd); } // ili PUT /api/artists/{id}
  updateSingle(fd: FormData){ return this.httpClient.put('/api/singles', fd); }     // ili PUT /api/singles/{id}
  updateAlbum(fd: FormData){ return this.httpClient.put('/api/albums', fd); }       // ili PUT /api/albums/{id}

  createArtist(payload: any): Observable<any> {
    return this.httpClient.post(`${environment.apiUrl}/artists`, payload, {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  getGenres(): Observable<Genre[]> {
    return this.httpClient.get<Genre[]>(`${environment.apiUrl}/genres`);
  }

  getFilteredContentByGenre(genre: any): Observable<any> {
    return this.httpClient.get(`${environment.apiUrl}/filter-genre`, { params: { genreName: genre } })
  }

  getFilteredContentByArtist(artistId: any): Observable<any> {
    return this.httpClient.get(`${environment.apiUrl}/filter-artist`, { params: { genreName: artistId } })
  }

  getMySubscriptions(): Observable<any[]> {
    return this.httpClient.get<any[]>(`${environment.apiUrl}/subscriptions`);
  }

  subscribe(payload: { targetId: string, subscriptionType: string, artistName?: string, imageUrl?: string}): Observable<any> {
    return this.httpClient.post(`${environment.apiUrl}/subscriptions`, payload);
  }

  unsubscribe(targetId: string): Observable<any> {
    return this.httpClient.delete(`${environment.apiUrl}/subscriptions/${targetId}`);
  }

}
