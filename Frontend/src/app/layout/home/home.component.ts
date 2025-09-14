import { Component } from '@angular/core';
import { Album, Artist, Song } from '../../content/models/model';
import { ContentService } from '../../content/content.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrl: './home.component.css'
})
export class HomeComponent {
  recommendedSongs: Song[] = []
  recommendedArtists: Artist[] = []
  recommendedAlbums: Album[] = []

  constructor(private contentService: ContentService) {

  }

  ngOnInit() {
    this.contentService.getRecommendedFeed().subscribe({
      next: (feed) => {
        this.recommendedSongs = feed.recommendedSongs;
        this.recommendedArtists = feed.recommendedArtists;
        this.recommendedAlbums = feed.recommendedAlbums;
      }
    })
  }

}
