import { Component, ElementRef, QueryList, ViewChildren } from '@angular/core';
import { Album, Song } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { AuthService } from '../../../auth/auth.service';
import { UpdateAlbumComponent } from '../update-album/update-album.component';
import { MatSnackBar } from '@angular/material/snack-bar';
@Component({
  selector: 'app-album-view',
  templateUrl: './album-view.component.html',
  styleUrl: './album-view.component.css'
})
export class AlbumViewComponent {
  album: Album = {
    title: "",
    artistIds: [],
    genres: [],
    coverKey: "",
    averageRating: null, 
    ratingCount: 0,
    artistNames: []
  }
  albumId: string;
  albumSingles: Song[] = []

  @ViewChildren('audioPlayer') audioPlayers!: QueryList<ElementRef<HTMLAudioElement>>;
  isPlaying = false;
  isAdmin = false;

  constructor(private contentService: ContentService, private snackBar: MatSnackBar,private router: Router,private auth: AuthService, private dialog: MatDialog) {
    const navigation = this.router.getCurrentNavigation();
    this.albumId = navigation?.extras?.state?.['albumId'];
    console.log(this.albumId)
    this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
}

  openEditAlbum(){
    const ref = this.dialog.open(UpdateAlbumComponent, {
      width: '720px',
      data: {
        album: this.album
      }
    });
   // ref.afterClosed().subscribe(ok => ok && this.reloadAlbum());
  }

  ngOnInit() {
    console.log(this.albumId)
    this.contentService.getAlbum(this.albumId).subscribe({
      next: (album: Album) => {
        this.album = album;
      }
    })
    this.contentService.getSongsByAlbum(this.albumId).subscribe({
      next: (songs: Song[]) => {
        this.albumSingles = songs
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
    this.contentService.getAlbum(this.albumId).subscribe({
      next: (album: Album) => {
        this.album = album;
        console.log(album)
      }
    })
    this.snackBar.open(`Thanks for rating ${this.album.title}: ${value}/5`, 'Close', { duration: 2500 });
  }
}
