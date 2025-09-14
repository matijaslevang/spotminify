import { Component, ElementRef, QueryList, ViewChildren } from '@angular/core';
import { Album } from '../../models/model';
import { ContentService } from '../../content.service';

@Component({
  selector: 'app-album-view',
  templateUrl: './album-view.component.html',
  styleUrl: './album-view.component.css'
})
export class AlbumViewComponent {
  album: Album = {
    name: "",
    artists: [],
    genres: [],
    imageUrl: "",
    songsUrls: [],
    rating: 4.5,
  }

  @ViewChildren('audioPlayer') audioPlayers!: QueryList<ElementRef<HTMLAudioElement>>;
  isPlaying = false;

  constructor(private contentService: ContentService) {}

  ngOnInit() {
    this.contentService.getAlbum().subscribe({
      next: (album: Album) => {
        this.album = album;
      }
    })
  }

  onPlay(currentAudio: HTMLAudioElement): void {
    this.audioPlayers.forEach(playerRef => {
      const player = playerRef.nativeElement;
      if (player !== currentAudio) {
        player.pause();
      }
    });
    this.isPlaying = true;
  }

  onPause(): void {
    this.isPlaying = this.audioPlayers.some(ref => !ref.nativeElement.paused);
  }
}
