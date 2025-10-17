import { Component, ElementRef, QueryList, ViewChildren } from '@angular/core';
import { Album } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { AuthService } from '../../../auth/auth.service';
import { UpdateAlbumComponent } from '../update-album/update-album.component';
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
  albumName: string;

  @ViewChildren('audioPlayer') audioPlayers!: QueryList<ElementRef<HTMLAudioElement>>;
  isPlaying = false;
  isAdmin = false;

  constructor(private contentService: ContentService, private router: Router,private auth: AuthService, private dialog: MatDialog) {
    const navigation = this.router.getCurrentNavigation();
    this.albumName = navigation?.extras?.state?.['albumName'];
    console.log(this.albumName)
    this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
}

  openEditAlbum(){
    const ref = this.dialog.open(UpdateAlbumComponent, {
      width: '720px',
      data: {
        album: this.album,                 // { albumId, name, artists[], genres[], imageUrl? ... }
        // artistOptions: this.artistOptions, // ili API
        // genreOptions: this.genreOptions
      }
    });
   // ref.afterClosed().subscribe(ok => ok && this.reloadAlbum());
  }

  ngOnInit() {
    this.contentService.getAlbum(this.albumName).subscribe({
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

  onAlbumRated(value: number) {
    console.log(`Album rated ${value}/5`);
    // po želji snackbar/toast
  }
}
