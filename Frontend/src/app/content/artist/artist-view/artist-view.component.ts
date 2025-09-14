import { Component } from '@angular/core';
import { Artist } from '../../models/model';
import { ContentService } from '../../content.service';

@Component({
  selector: 'app-artist-view',
  templateUrl: './artist-view.component.html',
  styleUrl: './artist-view.component.css'
})
export class ArtistViewComponent {
  artist: Artist = {
    name: '',
    bio: '',
    genres: [],
    imageUrl: ""
  }
  
  constructor(private contentService: ContentService) {}

  ngOnInit() {
    this.contentService.getArtist().subscribe({
      next: (artist: Artist) => {
        this.artist = artist;
      }
    })
  }
}
