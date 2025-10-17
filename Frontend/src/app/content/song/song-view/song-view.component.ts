import { Component } from '@angular/core';
import { Song } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { SongCacheService } from '../song-cache.service';
import { MatDialog } from '@angular/material/dialog';
import { AuthService } from '../../../auth/auth.service';
import { UpdateSongComponent } from '../update-song/update-song.component';

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
  audioSrc: string | null = null;
  isPlaying = false;
  isAdmin = false;
  constructor(private contentService: ContentService, private router: Router, private cache: SongCacheService, private auth: AuthService, private dialog: MatDialog) {
    const navigation = this.router.getCurrentNavigation();
    this.songName = navigation?.extras?.state?.['songName'];
    console.log(this.songName)
    this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
  }

  async ngOnInit() {
    const cached = await this.cache.getObjectUrl(this.song.songId!);
    this.audioSrc = cached ?? this.song.songUrl; // preferiraj keš
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
  onSongRated(value: number) {
    console.log(`Song rated with ${value}/5`);
    // po želji: prikaz poruke
    //this.snackBar.open(`Thanks for rating "${this.song.name}" ${value}/5`, 'Close', { duration: 2500 });
  }
  
  async onDownload(){
    await this.cache.download(this.song.songId!, this.song.songUrl);
    this.audioSrc = await this.cache.getObjectUrl(this.song.songId!);
  }

  async onRemove(){
    await this.cache.remove(this.song.songId!);
    this.audioSrc = this.song.songUrl;
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
