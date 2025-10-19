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

  ARTISTS: Artist[] = [
    {
      artistId: "artist-1",
      name: "Lana Del Rey",
      biography: "Known for her nostalgic and cinematic sound...",
      genres: ["Indie Pop", "Dream Pop"],
      imageUrl: "https://picsum.photos/id/1011/200/200"
    },
    {
      artistId: "artist-2",
      name: "Kendrick Lamar",
      biography: "Pulitzer-winning rapper known for his lyrical depth...",
      genres: ["Hip Hop", "Rap"],
      imageUrl: "https://picsum.photos/id/1027/200/200"
    },
    {
      artistId: "artist-3",
      name: "Adele",
      biography: "British singer famous for her emotional ballads...",
      genres: ["Pop", "Soul"],
      imageUrl: "https://picsum.photos/id/1015/200/200"
    },
    {
      artistId: "artist-4",
      name: "Arctic Monkeys",
      biography: "English indie rock band known for clever lyrics...",
      genres: ["Indie Rock", "Alternative"],
      imageUrl: "https://picsum.photos/id/1031/200/200"
    },
    {
      artistId: "artist-5",
      name: "Billie Eilish",
      biography: "Known for her whispery vocals and moody electropop sound.",
      genres: ["Pop", "Electropop"],
      imageUrl: "https://picsum.photos/id/1047/200/200"
    }
  ];

  SONGS: Song[] = [
    {
      name: "Summertime Sadness",
      artists: ["Lana Del Rey"],
      genres: ["Indie Pop", "Electropop"],
      imageUrl: "https://picsum.photos/id/1003/200/200",
      songUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
      rating: 4.8
    },
    {
      name: "HUMBLE.",
      artists: ["Kendrick Lamar"],
      genres: ["Hip Hop", "Rap"],
      imageUrl: "https://picsum.photos/id/1021/200/200",
      songUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
      rating: 4.9
    },
    {
      name: "Rolling in the Deep",
      artists: ["Adele"],
      genres: ["Pop", "Soul"],
      imageUrl: "https://picsum.photos/id/1040/200/200",
      songUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
      rating: 4.7
    },
    {
      name: "Do I Wanna Know?",
      artists: ["Arctic Monkeys"],
      genres: ["Indie Rock", "Alternative"],
      imageUrl: "https://picsum.photos/id/1062/200/200",
      songUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
      rating: 4.6
    }
  ];

  ALBUMS: Album[] = [
    {
      name: "Born to Die",
      artists: ["Lana Del Rey"],
      genres: ["Indie Pop", "Dream Pop"],
      imageUrl: "https://picsum.photos/id/1050/200/200",
      songsUrls: [
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"
      ],
      rating: 4.9
    },
    {
      name: "DAMN.",
      artists: ["Kendrick Lamar"],
      genres: ["Hip Hop", "Rap"],
      imageUrl: "https://picsum.photos/id/1035/200/200",
      songsUrls: [
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3"
      ],
      rating: 4.8
    },
    {
      name: "21",
      artists: ["Adele"],
      genres: ["Pop", "Soul"],
      imageUrl: "https://picsum.photos/id/1039/200/200",
      songsUrls: [
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3"
      ],
      rating: 4.9
    },
    {
      name: "AM",
      artists: ["Arctic Monkeys"],
      genres: ["Indie Rock", "Alternative"],
      imageUrl: "https://picsum.photos/id/1059/200/200",
      songsUrls: [
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
      ],
      rating: 4.7
    }
  ];

  getArtist(artistId: string): Observable<Artist> {
    return this.httpClient.get<Artist>(`${environment.apiUrl}/get-artist`, {
      params: { artistId: artistId }
    })
  }

  getSongsByArtist(artistName: string): Observable<Song[]> {
    const songs = this.SONGS.filter(song => song.artists.includes(artistName));
    return of(songs);
  }

  getAlbumsByArtist(artistName: string): Observable<Album[]> {
    const albums = this.ALBUMS.filter(album => album.artists.includes(artistName));
    return of(albums);
  }

  getSong(name: string): Observable<Song> {
    return of(this.SONGS.find(v => v.name === name))
  }

  getAlbum(name: string): Observable<Album> {
    return of(this.ALBUMS.find(v => v.name === name))
  }

  getRecommendedFeed(): Observable<any> {
    return of({
      recommendedArtists: this.ARTISTS,
      recommendedAlbums: this.ALBUMS,
      recommendedSongs: this.SONGS
    })
    //return this.httpClient.get(`${environment.apiUrl}/feed`)
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

  subscribe(payload: { targetId: string, subscriptionType: string }): Observable<any> {
    return this.httpClient.post(`${environment.apiUrl}/subscriptions`, payload);
  }

  unsubscribe(targetId: string): Observable<any> {
    return this.httpClient.delete(`${environment.apiUrl}/subscriptions/${targetId}`);
  }

}
