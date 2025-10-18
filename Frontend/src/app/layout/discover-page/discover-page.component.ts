import { Component } from '@angular/core';
import { Album, Artist, FilterDetails, Genre, Song } from '../../content/models/model';
import { ContentService } from '../../content/content.service';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-discover-page',
  templateUrl: './discover-page.component.html',
  styleUrl: './discover-page.component.css'
})
export class DiscoverPageComponent {
  resultSongs: FilterDetails[] = []
  resultArtists: FilterDetails[] = []
  resultAlbums: FilterDetails[] = []
  mySubscribedGenreIds = new Set<string>();
  
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
    this.contentService.getMySubscriptions().subscribe({
      next: (subscriptions) => {
        this.mySubscribedGenreIds = new Set(
          subscriptions
            .filter(sub => sub.subscriptionType === 'GENRE')
            .map(sub => sub.targetId)
        );
        console.log(this.mySubscribedGenreIds)
      },
      error: (err) => console.error("Could not load user's subscriptions", err)
    });
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

  isSubscribedTo(genreId: string): boolean {
    return this.mySubscribedGenreIds.has(genreId);
  }

  subscribeToGenre(): void {
    const selectedGenre = this.filterForm.get('genre')?.value;

    if (!selectedGenre) {
      this.snackBar.open('Please select a genre first.', 'Close', { duration: 3000 });
      return;
    }

    const payload = {
      targetId: selectedGenre.genreId,
      targetName: selectedGenre.genreName,
      subscriptionType: 'GENRE'
    };

    this.contentService.subscribe(payload).subscribe({
      next: () => {
        this.mySubscribedGenreIds.add(selectedGenre.genreId);
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
  unsubscribeFromGenre(): void {
    const selectedGenre = this.filterForm.get('genre')?.value;
    if (!selectedGenre) return;

    this.contentService.unsubscribe(selectedGenre.genreId).subscribe({
      next: () => {
        this.mySubscribedGenreIds.delete(selectedGenre.genreId);
        this.snackBar.open(`Unsubscribed from ${selectedGenre.genreName}`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Unsubscribe error:', err);
        this.snackBar.open('Failed to unsubscribe.', 'Close', { duration: 5000 });
      }
    });
  }
}
