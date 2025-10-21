import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Artist, FilterDetails } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';
import { AuthService } from '../../../auth/auth.service';
import { ContentService } from '../../content.service';
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

  constructor(private router: Router, private auth: AuthService, private contentService: ContentService) {}

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
    if (this.artist.artistId && confirm(`Delete ${this.artist.name} and ALL its content (albums, songs, files)? This action is irreversible!`)) {
      this.contentService.deleteArtist(this.artist.artistId).subscribe({
        next: (response) => {
          console.log('Artist deleted successfully', response);
          alert('Umetnik i sav njegov sadržaj uspešno obrisani!');
          // TODO: Dodati logiku za osvežavanje liste
        },
        error: (error) => {
          console.error('Error deleting artist:', error);
          alert(`Greška pri brisanju: ${error.message || error.statusText}`);
        }
      });
    }
  }
}
