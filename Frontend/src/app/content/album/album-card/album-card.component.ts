import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { Album } from '../../models/model';
import { Router } from '@angular/router';
import { FastAverageColor } from 'fast-average-color';

@Component({
  selector: 'app-album-card',
  templateUrl: './album-card.component.html',
  styleUrl: './album-card.component.css'
})
export class AlbumCardComponent {
  @ViewChild('albumCardImage') albumImageRef!: ElementRef<HTMLImageElement>;
  @Input() album: Album;

  dominantColor: string = "#ffffff";

  constructor(private router: Router) {}

  ngOnInit() {
    
  }

  ngAfterViewInit(): void {
    const img = this.albumImageRef.nativeElement
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      const fac = new FastAverageColor();
      const result = fac.getColor(img);
      this.dominantColor = result.hex;
    }
  }

  viewAlbum(): void {
    this.router.navigate(["/album"], {state: { albumName: this.album.name }});
  }
}
