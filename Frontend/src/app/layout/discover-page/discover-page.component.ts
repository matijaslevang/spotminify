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
  resultSongs: Song[] = []
  resultArtists: Artist[] = []
  resultAlbums: Album[] = []
  mySubscribedGenres = new Set<string>();
  
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
        this.mySubscribedGenres = new Set(
          subscriptions
            .filter(sub => sub.subscriptionType === 'GENRE')
            .map(sub => sub.targetId)
        );
        console.log(this.mySubscribedGenres)
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
          this.resultAlbums = filteredContent.resultAlbums.map((item: any) => item.content);
          this.resultArtists = filteredContent.resultArtists.map((item: any) => item.content);
          this.resultSongs = filteredContent.resultSongs.map((item: any) => item.content);
        }
      })
    }
    
  }

  isSubscribedTo(genre: string): boolean {
    return this.mySubscribedGenres.has(genre);
  }

  subscribeToGenre(): void {
    const selectedGenre = this.filterForm.get('genre')?.value;

    if (!selectedGenre) {
      this.snackBar.open('Please select a genre first.', 'Close', { duration: 3000 });
      return;
    }

    const payload = {
      targetId: selectedGenre.genreName,
      subscriptionType: 'GENRE',
      genres: [selectedGenre.genreName]
    };

    this.contentService.subscribe(payload).subscribe({
      next: () => {
        this.mySubscribedGenres.add(selectedGenre.genreName);
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

    this.contentService.unsubscribe(selectedGenre.genreName, "GENRE", [selectedGenre.genreName]).subscribe({
      next: () => {
        this.mySubscribedGenres.delete(selectedGenre.genreName);
        this.snackBar.open(`Unsubscribed from ${selectedGenre.genreName}`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Unsubscribe error:', err);
        this.snackBar.open('Failed to unsubscribe.', 'Close', { duration: 5000 });
      }
    });
  }
}
