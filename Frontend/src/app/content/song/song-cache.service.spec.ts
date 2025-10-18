import { TestBed } from '@angular/core/testing';

import { SongCacheService } from './song-cache.service';

describe('SongCacheService', () => {
  let service: SongCacheService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SongCacheService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
