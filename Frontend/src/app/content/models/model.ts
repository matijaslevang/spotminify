export interface Artist {
    artistId?: any;
    name: string,
    biography: string,
    genres: string[],
    imageUrl: string,
    averageRating?: number | null; 
    ratingCount?: number;
}

export interface Song {
    singleId?: any;
    title: string,
    artistIds: string[],
    genres: string[],
    imageKey: string,
    audioKey: string,
    averageRating?: number | null; 
    ratingCount?: number;
    artistNames: string[],
}

export interface Album {
    albumId?: any;
    title: string,
    artistIds: string[],
    genres: string[],
    coverKey: string,
    averageRating?: number | null; 
    ratingCount?: number;
    artistNames: string[],
}

export interface Genre {
  genreId: string;
  genreName: string;
}

export interface FilterDetails {
    contentName: string,
    contentId: string,
    imageUrl: string,
    contentGenres: string[],
    contentArtists?: string[]
}