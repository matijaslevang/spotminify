import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { Album, Artist, Song } from './models/model';

@Injectable({
  providedIn: 'root'
})
export class ContentService {
  constructor(private httpClient: HttpClient) { }

  album: Album = {
    name: "Graduation",
    artists: ["Yeezus", "Lil ricky"],
    genres: ["Rap", "Trap"],
    imageUrl: "https://m.media-amazon.com/images/I/71pxGj4RoVS._UF894,1000_QL80_.jpg",
    songsUrls: ["https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"],
    rating: 4.5,
  }

  artist: Artist = {
    name: 'Placeholder name',
    bio: 'Placeholder bio because why would we actually want to use any ai generated text when you can slam the keyboard and think of random words yourself',
    genres: ['J-pop', 'J-rock'],
    imageUrl: "https://interscope.com/cdn/shop/files/BLUE--STEELE-HSHRMobile.png?v=1752166443&width=900"
  }

  song: Song = {
    name: "ON SIGHT",
    artists: ["Ye"],
    genres: ["Rap", "Trap"],
    imageUrl: "https://m.media-amazon.com/images/I/71pxGj4RoVS._UF894,1000_QL80_.jpg",
    songUrl: "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    rating: 4.5,
  }

  getArtist(): Observable<Artist> {
    return of(this.artist)
  }

  getSong(): Observable<Song> {
    return of(this.song)
  }

  getAlbum(): Observable<Album> {
    return of(this.album)
  }
}
