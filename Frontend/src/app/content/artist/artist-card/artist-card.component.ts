import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Artist } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';
import { AuthService } from '../../../auth/auth.service';
@Component({
  selector: 'app-artist-card',
  templateUrl: './artist-card.component.html',
  styleUrl: './artist-card.component.css'
})
export class ArtistCardComponent {
  @ViewChild('artistCardImage') artistImageRef!: ElementRef<HTMLImageElement>;
  @Input() artist: Artist;
  isAdmin = false;

  dominantColor: string = "#ffffff";

  constructor(private router: Router, private auth: AuthService) {}

  ngOnInit() {
    this.auth.getUserRole().subscribe({
      next: (role) => {
        this.isAdmin = role === 'Admin'; 
      },
      error: (err) => {
        console.error('Error fetching user role', err);
        this.isAdmin = false;
      }
    });
  }

  ngAfterViewInit(): void {
    const img = this.artistImageRef.nativeElement
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      const fac = new FastAverageColor();
      const result = fac.getColor(img);
      this.dominantColor = result.hex;
    }
  }

  viewArtist(): void {
    this.router.navigate(["/artist"], {state: { artistName: this.artist.name }});
  }
  confirmDelete() {
  if (confirm(`Delete ${this.artist.name}?`)) {
    console.log('delete')
    //this.deleteArtist(); // tvoja implementacija
    }
  }
}
