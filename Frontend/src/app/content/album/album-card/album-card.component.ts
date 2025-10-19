import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Album, FilterDetails } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';
import { AuthService } from '../../../auth/auth.service';
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
    rating: 0
  };
  @Input() filterDetails: FilterDetails
  isAdmin: boolean = false;
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
  
  confirmDelete(){ 
    if(confirm(`Delete ${this.album.title}?`)) //this.deleteAlbum();
      console.log('delete')   
    }

}
