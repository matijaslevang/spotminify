import { Component } from '@angular/core';
import { Album, Artist, Song } from '../../content/models/model';
import { ContentService } from '../../content/content.service';
import { FormControl, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-discover-page',
  templateUrl: './discover-page.component.html',
  styleUrl: './discover-page.component.css'
})
export class DiscoverPageComponent {
  resultSongs: Song[] = []
  resultArtists: Artist[] = []
  resultAlbums: Album[] = []
  
  genres: string[] = []

  attemptedSearch: boolean = false;

  filterForm: FormGroup = new FormGroup({
    genre: new FormControl('', [Validators.required])
  })

  constructor(private contentService: ContentService) {

  }

  ngOnInit() {
    this.contentService.getAllGenres().subscribe({
      next: (genres: any) => {
        this.genres = genres;
      }
    })
  }

  applyFilters(): void {
    if (this.filterForm.valid) {
      this.attemptedSearch = true
      let selectedGenre = this.filterForm.get('genre').value
      this.contentService.getFilteredContentByGenre(selectedGenre).subscribe({
        next: (filteredContent: any) => {
          this.resultAlbums = filteredContent.resultAlbums
          this.resultArtists = filteredContent.resultArtists
          this.resultSongs = filteredContent.resultSongs
        }
      })
    }
    
  }
}
