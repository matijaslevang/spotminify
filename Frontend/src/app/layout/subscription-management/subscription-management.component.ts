import { Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ContentService } from '../../content/content.service';

@Component({
  selector: 'app-subscription-management',
  templateUrl: './subscription-management.component.html',
  styleUrls: ['./subscription-management.component.css']
})
export class SubscriptionManagementComponent implements OnInit {

  artistSubscriptions: any[] = [];
  genreSubscriptions: any[] = [];
  isLoading = true;

  constructor(
    private contentService: ContentService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.loadSubscriptions();
  }

  loadSubscriptions(): void {
    this.isLoading = true;
    this.contentService.getMySubscriptions().subscribe({
      next: (subscriptions) => {
        this.artistSubscriptions = subscriptions.filter(s => s.subscriptionType === 'ARTIST');
        this.genreSubscriptions = subscriptions.filter(s => s.subscriptionType === 'GENRE');
        console.log(this.genreSubscriptions)
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load subscriptions', err);
        this.isLoading = false;
        this.snackBar.open('Could not load your subscriptions.', 'Close', { duration: 3000 });
      }
    });
  }

  unsubscribe(subscription: any): void {
    this.contentService.unsubscribe(subscription.targetId).subscribe({
      next: () => {
        if (subscription.subscriptionType === 'ARTIST') {
          this.artistSubscriptions = this.artistSubscriptions.filter(s => s.targetId !== subscription.targetId);
        } else if (subscription.subscriptionType === 'GENRE') {
          this.genreSubscriptions = this.genreSubscriptions.filter(s => s.targetId !== subscription.targetId);
        }
        
        this.snackBar.open(`Unsubscribed from ${subscription.targetName}`, 'Close', { duration: 2000 });
      },
      error: (err) => {
        console.error('Failed to unsubscribe', err);
        this.snackBar.open('An error occurred. Please try again.', 'Close', { duration: 3000 });
      }
    });
  }
}