export interface BasicAccountType {
    username: string;
    id: number;
}

export interface PostType {
    id: number;
    author: BasicAccountType;
    content: string;
    created_at: string;
    updated_at: string;
    parent: number | null;
    original_post: number | null;
    likes: number;
    comments: number;
    views: number;
    likes_count: number;
    is_liked: boolean;
}

export interface PaginatedPostsType {
    next: number | null;
    previous: number | null;
    count: number;
    results: PostType[];
}

export interface CreatePostData {
    content: string;
    tagged_accounts: string[];
}
