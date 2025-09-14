import { Component } from '@angular/core';
import { Song } from '../../models/model';
import { ContentService } from '../../content.service';

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

  isPlaying = false;

  constructor(private contentService: ContentService) {}

  ngOnInit() {
    this.contentService.getSong().subscribe({
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
