import { AfterViewInit, Component, ElementRef, Input, ViewChild } from '@angular/core';
import { FilterDetails, Song } from '../../models/model';
import { FastAverageColor } from 'fast-average-color';
import { Router } from '@angular/router';
import { AuthService } from '../../../auth/auth.service';
@Component({
  selector: 'app-song-card',
  templateUrl: './song-card.component.html',
  styleUrl: './song-card.component.css'
})
export class SongCardComponent implements AfterViewInit {
  @ViewChild('songCardImage') songImageRef!: ElementRef<HTMLImageElement>;
  @Input() song: Song = {
    title: '',
    artistIds: [],
    genres: [],
    imageKey: '',
    audioKey: '',
    rating: 0
  };
  @Input() filterDetails: FilterDetails

  dominantColor: string = "#ffffff";
  isAdmin = false;

  constructor(private router: Router, private auth: AuthService) {}

  ngOnInit() {
    this.auth.getUserRole().subscribe({
      next: role => this.isAdmin = role === 'Admin', 
      error: () => this.isAdmin = false
    });
    if (this.filterDetails) {
      this.song.title = this.filterDetails.contentName
      this.song.singleId = this.filterDetails.contentId
      this.song.imageKey = this.filterDetails.imageUrl
      this.song.artistIds = this.filterDetails.contentArtists
      this.song.genres = this.filterDetails.contentGenres
    }
  }

  ngAfterViewInit(): void {
    const img = this.songImageRef.nativeElement
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      const fac = new FastAverageColor();
      const result = fac.getColor(img);
      this.dominantColor = result.hex;
    }
  }

  viewSong(): void {
    this.router.navigate(["/song"], {state: { songId: this.song.singleId}});
  }
  
  confirmDelete() {
    if (confirm(`Delete ${this.song.title}?`)) {
      console.log('delete'); // TODO: pozovi servis za brisanje
    }
  }
}
