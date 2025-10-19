import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Artist, FilterDetails } from '../../models/model';
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
  @Input() artist: Artist = {
    name: '',
    biography: '',
    genres: [],
    imageUrl: ''
  };
  @Input() filterDetails: FilterDetails
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
    if (this.filterDetails) {
      this.artist.name = this.filterDetails.contentName
      this.artist.artistId = this.filterDetails.contentId
      this.artist.imageUrl = this.filterDetails.imageUrl
      this.artist.genres = this.filterDetails.contentGenres
    }
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
    this.router.navigate(["/artist"], {state: { artistId: this.artist.artistId }});
  }
  confirmDelete() {
  if (confirm(`Delete ${this.artist.name}?`)) {
    console.log('delete')
    //this.deleteArtist(); // tvoja implementacija
    }
  }
}
