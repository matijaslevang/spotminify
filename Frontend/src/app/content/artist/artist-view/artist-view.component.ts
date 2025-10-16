import { Component } from '@angular/core';
import { Artist } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';

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
  artistName: string;

  constructor(private contentService: ContentService, private router: Router) {
    const navigation = this.router.getCurrentNavigation();
    this.artistName = navigation?.extras?.state?.['artistName'];
    console.log(this.artistName)
  }

  ngOnInit() {
    this.contentService.getArtist(this.artistName).subscribe({
      next: (artist: Artist) => {
        this.artist = artist;
      }
    })
  }
}
