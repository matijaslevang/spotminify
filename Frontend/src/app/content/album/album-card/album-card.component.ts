import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Album, FilterDetails } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';
import { AuthService } from '../../../auth/auth.service';
import { ContentService } from '../../content.service';
@Component({
  selector: 'app-album-card',
  templateUrl: './album-card.component.html',
  styleUrl: './album-card.component.css'
})
export class AlbumCardComponent {
  @ViewChild('albumCardImage') albumImageRef!: ElementRef<HTMLImageElement>;
  @Input() album: Album = {
    title: '',
    artistIds: [],
    genres: [],
    coverKey: '',
    averageRating: 0,
    ratingCount:0
  };
  @Input() filterDetails: FilterDetails
  isAdmin: boolean = false;
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
      this.album.title = this.filterDetails.contentName
      this.album.albumId = this.filterDetails.contentId
      this.album.coverKey = this.filterDetails.imageUrl
      this.album.genres = this.filterDetails.contentGenres
      this.album.artistIds = this.filterDetails.contentArtists
    }
  }

  ngAfterViewInit(): void {
    const img = this.albumImageRef.nativeElement
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      const fac = new FastAverageColor();
      const result = fac.getColor(img);
      this.dominantColor = result.hex;
    }
  }

  viewAlbum(): void {
    this.router.navigate(["/album"], {state: { albumId: this.album.albumId }});
  }

  confirmDelete() { 
      if(this.album.albumId && confirm(`Delete ${this.album.title} and all its songs?`)) {
          this.contentService.deleteAlbum(this.album.albumId).subscribe({
              next: (response) => {
                  console.log('Album deleted successfully', response);
                  alert('Album i sve pesme uspešno obrisani!');
                  // TODO: Dodati navigaciju ili osvežavanje liste albuma
              },
              error: (error) => {
                  console.error('Error deleting album:', error);
                  alert(`Greška pri brisanju: ${error.message || error.statusText}`);
              }
          });
      }
  }

}
