import { Component } from '@angular/core';
import { Song } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { SongCacheService } from '../song-cache.service';
import { MatDialog } from '@angular/material/dialog';
import { AuthService } from '../../../auth/auth.service';
import { UpdateSongComponent } from '../update-song/update-song.component';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-song-view',
  templateUrl: './song-view.component.html',
  styleUrl: './song-view.component.css'
})
export class SongViewComponent {
  song: Song = {
    title: "",
    artistIds: [],
    genres: [],
    imageKey: "",
    audioKey: "",
    averageRating: null, 
    ratingCount: 0,
    artistNames: []
  }
  songId: string = "";

  cachedAudioSrc: string | null = null; 
  isCached = false; 
  isPlaying = false;

  isAdmin = false;
  constructor(private contentService: ContentService, private snackBar: MatSnackBar,private router: Router, private cache: SongCacheService, private auth: AuthService, private dialog: MatDialog) {
    const navigation = this.router.getCurrentNavigation();
    this.songId = navigation?.extras?.state?.['songId'];
    console.log(this.songId)
    this.auth.getUserRole().subscribe(r => {
    console.log('Dobijena korisnička uloga (Role):', r); // Loguje samo ulogu
    this.isAdmin = (r === 'Admin' || r === 'ADMIN');
  });
    //this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
  }

  async ngOnInit() {
    this.contentService.getSong(this.songId).subscribe({
      next: async (song: Song) => {
        this.song = song;
        await this.checkCacheStatus(); 
        console.log(song)
      }
    })
  }

  async checkCacheStatus(): Promise<void> {
    const songId = this.song.singleId!; 
    const cachedUrl = await this.cache.getObjectUrl(songId); 
    this.isCached = !!cachedUrl; 
    this.cachedAudioSrc = cachedUrl; 

    if (cachedUrl) {
        console.log("Offline version available.");
    }
  }

  onPlay(): void {
    this.isPlaying = true;
  }

  onPause(): void {
    this.isPlaying = false;
  }
  onSongRated(value: number) {
    console.log(`Song rated with ${value}/5`);
    this.contentService.getSong(this.songId).subscribe({
      next: (song: Song) => {
        this.song = song;
        console.log(song)
      }
    })
    this.snackBar.open(`Thanks for rating "${this.song.title}" ${value}/5`, 'Close', { duration: 2500 });
  }
  
  async onDownload(){
    const downloadUrl = this.song.audioKey; 
    try {
        this.snackBar.open(`Downloading ${this.song.title}...`, 'Close');
        await this.cache.download(this.song.singleId!, downloadUrl); 
        await this.checkCacheStatus(); 

        this.snackBar.open(`${this.song.title} ready for offline use!`, 'Close', { duration: 3000 });
    } catch (e) {
        this.snackBar.open(`Download failed! Check console.`, 'Close', { duration: 3000 });
    }
  }
  
  openEditSingle(){
  const ref = this.dialog.open(UpdateSongComponent, {
    width: '680px',
    data: {
      single: this.song,              
      selectedAritsts: this.song.artistNames,
      availableGenres: this.song.genres
    }
  });
  ref.afterClosed().subscribe(ok => ok && this.reloadSong());
}
  reloadSong(){
    this.contentService.getSong(this.songId).subscribe({
        next: async (song: Song) => {
          this.song = song;
          await this.checkCacheStatus(); 
          console.log(song)
        }
      })
  }
}
