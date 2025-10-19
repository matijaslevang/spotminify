import { Component, OnInit } from '@angular/core';
import { Artist, Song, Album } from '../../models/model';
import { ContentService } from '../../content.service';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../../../auth/auth.service';
import { UpdateArtistComponent } from '../update-artist/update-artist.component';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-artist-view',
  templateUrl: './artist-view.component.html',
  styleUrls: ['./artist-view.component.css']
})
export class ArtistViewComponent implements OnInit {
  artist: Artist;
  artistSongs: Song[] = [];
  artistAlbums: Album[] = [];
  artistId: string;
  
  isLoading = true;
  mySubscribedArtistIds = new Set<string>();
  isAdmin = false;
  constructor(
    private contentService: ContentService, 
    private router: Router,
    private snackBar: MatSnackBar,
    private auth: AuthService,
    private dialog: MatDialog,
  ) {
    this.artistId = history.state.artistId;
    console.log("Artist name from history.state:", this.artistId);
  }

  ngOnInit(): void {
    if (this.artistId) {
      this.loadArtistData(this.artistId);
      this.loadMySubscriptions();
      this.auth.getUserRole().subscribe(r => this.isAdmin = (r === 'Admin' || r === 'ADMIN'));
    } else {
      console.error("Artist name not found in state, redirecting.");
      this.router.navigate(['/discover']);
    }
  }
  openEditArtist(){
    const ref = this.dialog.open(UpdateArtistComponent, {
      width: '720px',
      data: { artist: this.artist, availableGenres: this.artistSongs } // prosledi šta već imaš
    });
    ref.afterClosed().subscribe(saved => { if (saved) this.loadArtistData(this.artist.name); });
  }
  loadArtistData(artistId: string): void {
    this.isLoading = true;
    this.contentService.getArtist(artistId).subscribe({
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
  onArtistRated(value: number) {
  this.snackBar.open(`Thanks for rating ${this.artist.name}: ${value}/5`, 'Close', { duration: 2500 });
}

}