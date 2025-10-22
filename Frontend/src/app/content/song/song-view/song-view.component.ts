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
    ratingCount: 0
  }
  songId: string = "";
  audioSrc: string | null = null;
  isPlaying = false;
  isAdmin = false;
  constructor(private contentService: ContentService, private snackBar: MatSnackBar,private router: Router, private cache: SongCacheService, private auth: AuthService, private dialog: MatDialog) {
    const navigation = this.router.getCurrentNavigation();
    this.songId = navigation?.extras?.state?.['songId'];
    console.log(this.songId)
    this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
  }

  async ngOnInit() {
    const cached = await this.cache.getObjectUrl(this.song.singleId!);
    this.audioSrc = cached ?? this.song.audioKey; // preferiraj keš
    this.contentService.getSong(this.songId).subscribe({
      next: (song: Song) => {
        this.song = song;
        console.log(song)
      }
    })
  }

  onPlay(): void {
    this.isPlaying = true;
  }

  onPause(): void {
    this.isPlaying = false;
  }
  onSongRated(value: number) {
    console.log(`Song rated with ${value}/5`);
    this.snackBar.open(`Thanks for rating "${this.song.title}" ${value}/5`, 'Close', { duration: 2500 });
  }
  
  async onDownload(){
    await this.cache.download(this.song.singleId!, this.song.audioKey);
    this.audioSrc = await this.cache.getObjectUrl(this.song.singleId!);
  }

  async onRemove(){
    await this.cache.remove(this.song.singleId!);
    this.audioSrc = this.song.audioKey;
  }
  openEditSingle(){
  const ref = this.dialog.open(UpdateSongComponent, {
    width: '680px',
    data: {
      single: this.song,                 // očekuje { songId, name, artists[], genres[], imageUrl?, explicit? ... }
      //artistOptions: this.artistOptions, // ili dohvati sa API-ja
      //genreOptions: this.genreOptions
    }
  });
  //ref.afterClosed().subscribe(ok => ok && this.reloadSong());
}
}
