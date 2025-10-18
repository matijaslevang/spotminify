import { AfterViewInit, Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Song } from '../../models/model';
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
  @Input() song: Song;

  dominantColor: string = "#ffffff";
  isAdmin = false;

  constructor(private router: Router, private auth: AuthService) {}

  ngOnInit() {
    this.auth.getUserRole().subscribe({
      next: role => this.isAdmin = role === 'Admin', 
      error: () => this.isAdmin = false
    });
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
    this.router.navigate(["/song"], {state: { songName: this.song.name}});
  }
  
  confirmDelete() {
    if (confirm(`Delete ${this.song.name}?`)) {
      console.log('delete'); // TODO: pozovi servis za brisanje
    }
  }
}
