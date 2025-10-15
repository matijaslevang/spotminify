import { Component } from '@angular/core';
import { Album, Artist, Genre, Song } from '../../content/models/model';
import { ContentService } from '../../content/content.service';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-discover-page',
  templateUrl: './discover-page.component.html',
  styleUrl: './discover-page.component.css'
})
export class DiscoverPageComponent {
  resultSongs: Song[] = []
  resultArtists: Artist[] = []
  resultAlbums: Album[] = []
  
  genres: Genre[] = []

  attemptedSearch: boolean = false;

  filterForm: FormGroup = new FormGroup({
    genre: new FormControl('', [Validators.required])
  })

  constructor(private contentService: ContentService, private snackBar: MatSnackBar) {

  }

  ngOnInit() {
    this.contentService.getGenres().subscribe({
      next: (genres: any) => {
        this.genres = genres;
      }
    })
  }

  applyFilters(): void {
    if (this.filterForm.valid) {
      this.attemptedSearch = true
      let selectedGenre = this.filterForm.get('genre').value
      this.contentService.getFilteredContentByGenre(selectedGenre.genreName).subscribe({
        next: (filteredContent: any) => {
          this.resultAlbums = filteredContent.resultAlbums
          this.resultArtists = filteredContent.resultArtists
          this.resultSongs = filteredContent.resultSongs
        }
      })
    }
    
  }

  subscribeToGenre(): void {
    const selectedGenre = this.filterForm.get('genre')?.value;

    if (!selectedGenre) {
      this.snackBar.open('Please select a genre first.', 'Close', { duration: 3000 });
      return;
    }

    const payload = {
      targetId: selectedGenre.genreId,
      subscriptionType: 'GENRE'
    };

    this.contentService.subscribe(payload).subscribe({
      next: () => {
        this.snackBar.open(`Successfully subscribed to ${selectedGenre.genreName}!`, 'Close', {
          duration: 3000,
          panelClass: ['success-snackbar']
        });
      },
      error: (err) => {
        console.error('Subscription error:', err);
        const message = err?.error?.message || 'Failed to subscribe. You might be already subscribed.';
        this.snackBar.open(message, 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }
}
