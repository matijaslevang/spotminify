import { Component } from '@angular/core';
import { Song } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-song-view',
  templateUrl: './song-view.component.html',
  styleUrl: './song-view.component.css'
})
export class SongViewComponent {
  song: Song = {
    name: "",
    artists: [],
    genres: [],
    imageUrl: "",
    songUrl: "",
    rating: 4.5,
  }
  songName: string = "";

  isPlaying = false;

  constructor(private contentService: ContentService, private router: Router) {
    const navigation = this.router.getCurrentNavigation();
    this.songName = navigation?.extras?.state?.['songName'];
    console.log(this.songName)
  }

  ngOnInit() {
    this.contentService.getSong(this.songName).subscribe({
      next: (song: Song) => {
        this.song = song;
      }
    })
  }

  onPlay(): void {
    this.isPlaying = true;
  }

  onPause(): void {
    this.isPlaying = false;
  }

  
}
