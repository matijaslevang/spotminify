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
        console.log(feed)
        this.recommendedSongs = feed.recommendedSongs
          .sort((a: any, b: any) => b.score - a.score)
          .map((item: any) => item.content);

        this.recommendedArtists = feed.recommendedArtists
          .sort((a: any, b: any) => b.score - a.score)
          .map((item: any) => item.content);

        this.recommendedAlbums = feed.recommendedAlbums
          .sort((a: any, b: any) => b.score - a.score)
          .map((item: any) => item.content);
      }
    })
  }

}
