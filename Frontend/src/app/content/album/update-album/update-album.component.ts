import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../../content.service';

@Component({
  selector: 'app-update-album',
  templateUrl: './update-album.component.html',
  styleUrl: './update-album.component.css'
})
export class UpdateAlbumComponent {
cover?: File;
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    public ref: MatDialogRef<UpdateAlbumComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      album: any;                  // { albumId | id, name, genres[], artists[] ... }
      genreOptions: string[];
      artistOptions: {id:string,name:string}[];
    }
  ){
    const a = data.album ?? {};
    this.form = this.fb.group({
      title: [a.name ?? '', Validators.required],
      genres: [a.genres ?? [], Validators.required],
      artistIds: [a.artistsIds ?? [], Validators.required]
    });
  }

  onCover(e: Event){
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) this.cover = f;
  }

  save(){
    if (this.form.invalid) return;

    const fd = new FormData();
    fd.append('albumId', String(this.data.album.albumId ?? this.data.album.id));
    fd.append('title', this.form.get('title')!.value);
    for (const g of (this.form.get('genres')!.value as string[])) fd.append('genres', g);
    for (const a of (this.form.get('artistIds')!.value as string[])) fd.append('artistIds', a);
    if (this.cover) fd.append('cover', this.cover);

    this.api.updateAlbum(fd).subscribe({
      next: () => this.ref.close(true),
      error: () => this.ref.close(false)
    });
  }

  cancel(){ this.ref.close(false); }
}