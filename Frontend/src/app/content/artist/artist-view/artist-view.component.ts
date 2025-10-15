import { Component, OnInit } from '@angular/core';
import { Artist, Song, Album } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-artist-view',
  templateUrl: './artist-view.component.html',
  styleUrls: ['./artist-view.component.css']
})
export class ArtistViewComponent implements OnInit {
  artist: Artist;
  artistSongs: Song[] = [];
  artistAlbums: Album[] = [];
  artistName: string;
  
  isLoading = true;
  mySubscribedArtistIds = new Set<string>();

  constructor(
    private contentService: ContentService, 
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.artistName = history.state.artistName;
    console.log("Artist name from history.state:", this.artistName);
  }

  ngOnInit(): void {
    if (this.artistName) {
      this.loadArtistData(this.artistName);
      this.loadMySubscriptions();
    } else {
      console.error("Artist name not found in state, redirecting.");
      this.router.navigate(['/discover']);
    }
  }

  loadArtistData(artistName: string): void {
    this.isLoading = true;
    this.contentService.getArtist(artistName).subscribe({
      next: (artist: Artist) => {
        this.artist = artist;
        // Will be changed
        this.loadContentForArtist(artist.name); 
        this.isLoading = false;
      },
      error: (err) => {
        console.error("Failed to load artist", err);
        this.isLoading = false;
        this.router.navigate(['/discover']);
      }
    });
  }
  loadContentForArtist(artistName: string): void {
    this.contentService.getSongsByArtist(artistName).subscribe(songs => {
      this.artistSongs = songs;
    });
    this.contentService.getAlbumsByArtist(artistName).subscribe(albums => {
      this.artistAlbums = albums;
    });
  }

  loadMySubscriptions(): void {
    this.contentService.getMySubscriptions().subscribe({
      next: (subscriptions) => {
        this.mySubscribedArtistIds = new Set(
          subscriptions
            .filter(sub => sub.subscriptionType === 'ARTIST')
            .map(sub => sub.targetId)
        );
      },
      error: (err) => console.error("Could not load user's subscriptions", err)
    });
  }

  isSubscribedTo(artistId: string): boolean {
    return this.mySubscribedArtistIds.has(artistId);
  }

  subscribeToArtist(): void {
    if (!this.artist?.artistId) return;
    const payload = { targetId: this.artist.artistId, subscriptionType: 'ARTIST' };
    this.contentService.subscribe(payload).subscribe({
      next: () => {
        this.mySubscribedArtistIds.add(this.artist.artistId);
        this.snackBar.open(`Successfully subscribed to ${this.artist.name}!`, 'Close', { duration: 3000 });
      },
      error: (err) => this.snackBar.open('Failed to subscribe.', 'Close', { duration: 3000 })
    });
  }

  unsubscribeFromArtist(): void {
    if (!this.artist?.artistId) return;
    this.contentService.unsubscribe(this.artist.artistId).subscribe({
      next: () => {
        this.mySubscribedArtistIds.delete(this.artist.artistId);
        this.snackBar.open(`Unsubscribed from ${this.artist.name}`, 'Close', { duration: 3000 });
      },
      error: (err) => this.snackBar.open('Failed to unsubscribe.', 'Close', { duration: 3000 })
    });
  }
}