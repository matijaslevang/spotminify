import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../../content.service';
@Component({
  selector: 'app-update-song',
  templateUrl: './update-song.component.html',
  styleUrl: './update-song.component.css'
})
export class UpdateSongComponent {
file?: File;               // zamena cover-a (opciono)
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    public ref: MatDialogRef<UpdateSongComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      single: any;           // očekuje { songId | id, name, genres[], artists[], explicit? }
      genreOptions: string[];
      artistOptions: {id:string,name:string}[];
    }
  ){
    const s = data.single ?? {};
    this.form = this.fb.group({
      title: [s.name ?? '', Validators.required],
      genres: [s.genres ?? [], Validators.required],
      artistIds: [s.artistsIds ?? [], Validators.required],
      explicit: [!!s.explicit]
    });
  }

  onFile(e: Event){
    const input = e.target as HTMLInputElement;
    const f = input.files?.[0];
    if (f) this.file = f;
  }

  save(){
    if (this.form.invalid) return;

    const fd = new FormData();
    fd.append('songId', String(this.data.single.songId ?? this.data.single.id));
    fd.append('title', this.form.get('title')!.value);
    for (const g of (this.form.get('genres')!.value as string[])) fd.append('genres', g);
    for (const a of (this.form.get('artistIds')!.value as string[])) fd.append('artistIds', a);
    fd.append('explicit', String(!!this.form.get('explicit')!.value));
    if (this.file) fd.append('image', this.file);

    // this.api.updateSingle(fd).subscribe({
    //   next: () => this.ref.close(true),
    //   error: () => this.ref.close(false)
    // });
  }

  cancel(){ this.ref.close(false); }
}