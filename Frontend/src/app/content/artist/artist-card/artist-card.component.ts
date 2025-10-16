import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Artist } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';

@Component({
  selector: 'app-artist-card',
  templateUrl: './artist-card.component.html',
  styleUrl: './artist-card.component.css'
})
export class ArtistCardComponent {
  @ViewChild('artistCardImage') artistImageRef!: ElementRef<HTMLImageElement>;
  @Input() artist: Artist;

  dominantColor: string = "#ffffff";

  constructor(private router: Router) {}

  ngOnInit() {
    
  }

  ngAfterViewInit(): void {
    const img = this.artistImageRef.nativeElement
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      const fac = new FastAverageColor();
      const result = fac.getColor(img);
      this.dominantColor = result.hex;
    }
  }

  viewArtist(): void {
    this.router.navigate(["/artist"], {state: { artistName: this.artist.name }});
  }
}
