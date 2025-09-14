import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { Album, Artist, Song } from './models/model';
import { environment } from '../../enviroment';

@Injectable({
  providedIn: 'root'
})
export class ContentService {
  constructor(private httpClient: HttpClient) { }

  ARTISTS: Artist[] = [
    {
      name: "Lana Del Rey",
      bio: "Known for her nostalgic and cinematic sound, blending indie pop and dream pop influences.",
      genres: ["Indie Pop", "Dream Pop"],
      imageUrl: "https://picsum.photos/id/1011/200/200"
    },
    {
      name: "Kendrick Lamar",
      bio: "Pulitzer-winning rapper known for his lyrical depth and powerful social commentary.",
      genres: ["Hip Hop", "Rap"],
      imageUrl: "https://picsum.photos/id/1027/200/200"
    },
    {
      name: "Adele",
      bio: "British singer famous for her emotional ballads and powerhouse vocals.",
      genres: ["Pop", "Soul"],
      imageUrl: "https://picsum.photos/id/1015/200/200"
    },
    {
      name: "Arctic Monkeys",
      bio: "English indie rock band known for clever lyrics and genre-bending albums.",
      genres: ["Indie Rock", "Alternative"],
      imageUrl: "https://picsum.photos/id/1031/200/200"
    },
    {
      name: "Billie Eilish",
      bio: "Known for her whispery vocals and moody electropop sound.",
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

  getArtist(name: string): Observable<Artist> {
    return of(this.ARTISTS.find(v => v.name === name))
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
  }

createArtist(payload: any): Observable<any> {
    return this.httpClient.post(`${environment.apiUrl}/artists`, payload, {
      headers: { 'Content-Type': 'application/json' }
    });
  }

}
