document.addEventListener('DOMContentLoaded', () => {
    // Initialize Socket.IO
    const socket = io();
    
    // User menu functionality
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userMenuDropdown = document.getElementById('userMenuDropdown');
    const logoutBtn = document.getElementById('logoutBtn');
    const settingsBtn = document.getElementById('settingsBtn');
    const likedPostsBtn = document.getElementById('likedPostsBtn');
    const myPostsBtn = document.getElementById('myPostsBtn');
    const newPostBtn = document.getElementById('newPostBtn');
    const modalOverlay = document.getElementById('modalOverlay');
    const postForm = document.getElementById('postForm');
    const appName = document.querySelector('.app-name');

    // Load initial posts
    loadInitialPosts();

    // Add click event for app name
    appName.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        const postsContainer = document.getElementById('postsContainer');
        postsContainer.innerHTML = ''; // Clear existing posts
        loadInitialPosts();
        // Reset active states of filter buttons
        likedPostsBtn.classList.remove('active');
        myPostsBtn.classList.remove('active');
    });


    // Listen for new posts via WebSocket
    socket.on('new_post', (post) => {
        addNewPost(post);
    });

    // Listen for like updates via WebSocket
    socket.on('like_update', (data) => {
        updatePostLikes(data);
    });

    // Toggle user menu
    userMenuBtn.addEventListener('click', () => {
        userMenuDropdown.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    window.addEventListener('click', (event) => {
        if (!event.target.matches('.user-menu-button') && 
            !event.target.matches('.dropdown-arrow') && 
            !event.target.matches('#username')) {
            if (userMenuDropdown.classList.contains('show')) {
                userMenuDropdown.classList.remove('show');
            }
        }
    });

    // New Post Modal
    newPostBtn.addEventListener('click', () => {
        modalOverlay.classList.add('show');
    });

    // Close modal when clicking outside
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });

    // Close modal with cancel button
    document.querySelector('.modal-button.cancel').addEventListener('click', closeModal);

    // Handle post submission
    postForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('postContent').value.trim();
        
        if (!content) {
            alert('Please enter some content for your post.');
            return;
        }

        try {
            const response = await fetch('/posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            if (response.ok) {
                closeModal();
                document.getElementById('postContent').value = '';
            } else {
                const error = await response.json();
                alert(error.error || 'Failed to create post');
            }
        } catch (error) {
            console.error('Error creating post:', error);
            alert('Failed to create post. Please try again.');
        }
    });

    // Logout functionality
    logoutBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                window.location.href = '/';
            }
        } catch (error) {
            console.error('Logout failed:', error);
        }
    });

    // Settings button (placeholder)
    settingsBtn.addEventListener('click', () => {
        console.log('Settings clicked - functionality not implemented yet');
    });

    // Side menu buttons (placeholders)
    likedPostsBtn.addEventListener('click', async () => {
        const isCurrentlyActive = likedPostsBtn.classList.contains('active');
        
        if (isCurrentlyActive) {
            // If already active, remove active class and show all posts
            likedPostsBtn.classList.remove('active');
            loadInitialPosts();
        } else {
            // If not active, add active class and show only liked posts
            try {
                const response = await fetch('/posts/liked');
                if (response.ok) {
                    const posts = await response.json();
                    displayPosts(posts);
                    likedPostsBtn.classList.add('active');
                    myPostsBtn.classList.remove('active');
                } else {
                    console.error('Failed to fetch liked posts');
                }
            } catch (error) {
                console.error('Error fetching liked posts:', error);
            }
        }
    });

    myPostsBtn.addEventListener('click', async () => {
        const isCurrentlyActive = myPostsBtn.classList.contains('active');
        
        if (isCurrentlyActive) {
            // If already active, remove active class and show all posts
            myPostsBtn.classList.remove('active');
            loadInitialPosts();
        } else {
            // If not active, add active class and show only my posts
            try {
                const response = await fetch('/posts/my');
                if (response.ok) {
                    const posts = await response.json();
                    displayPosts(posts);
                    myPostsBtn.classList.add('active');
                    likedPostsBtn.classList.remove('active');
                } else {
                    console.error('Failed to fetch my posts');
                }
            } catch (error) {
                console.error('Error fetching my posts:', error);
            }
        }
    });
});

function closeModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.classList.remove('show');
    document.getElementById('postContent').value = '';
}

async function loadInitialPosts() {
    try {
        const response = await fetch('/posts');
        if (response.ok) {
            const posts = await response.json();
            displayPosts(posts);
        }
    } catch (error) {
        console.error('Failed to load posts:', error);
    }
}

function displayPosts(posts) {
    const postsContainer = document.getElementById('postsContainer');
    postsContainer.innerHTML = ''; // Clear existing posts

    if (!posts.length) {
        postsContainer.innerHTML = '<p class="no-posts">No posts available.</p>';
        return;
    }

    posts.forEach(post => {
        const postElement = createPostElement(post);
        postsContainer.appendChild(postElement);
    });
}

function addNewPost(post) {
    const postsContainer = document.getElementById('postsContainer');
    const noPostsMessage = postsContainer.querySelector('.no-posts');
    
    if (noPostsMessage) {
        noPostsMessage.remove();
    }

    const postElement = createPostElement(post);
    postsContainer.insertBefore(postElement, postsContainer.firstChild);
}

function createPostElement(post) {
    const postDiv = document.createElement('div');
    postDiv.className = 'post';
    postDiv.dataset.postId = post.id;

    const likeButtonClass = post.liked ? 'like-button liked' : 'like-button';
    const likeButtonDisabled = post.isAuthor ? 'disabled' : '';

    // Check for URLs in post content and make them clickable
    const postContent = convertUrlsToLinks(post.content);

    postDiv.innerHTML = `
        <div class="post-header">
            <span class="post-author">${post.username}</span>
            <span class="post-date">${new Date(post.created_at).toLocaleDateString()}</span>
        </div>
        <div class="post-content">${postContent}</div>
        <div class="post-actions">
            <button class="${likeButtonClass}" onclick="toggleLike(${post.id})" ${likeButtonDisabled}>
                ♥ ${post.likes || 0}
            </button>
        </div>
    `;
    return postDiv;
}

// Function to convert URLs in text to clickable links
function convertUrlsToLinks(text) {
    const urlPattern = /(https?:\/\/[^\s]+)/g; // Regex to match URLs starting with http:// or https://
    return text.replace(urlPattern, '<br><a href="$1" target="_blank">$1</a>');
}


async function toggleLike(postId) {
    try {
        const response = await fetch(`/posts/${postId}/like`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            if (error.error === 'Cannot like your own post') {
                alert('You cannot like your own post');
            } else {
                alert(error.error || 'Failed to update like');
            }
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        alert('Failed to update like. Please try again.');
    }
}

function updatePostLikes(data) {
    const postElement = document.querySelector(`[data-post-id="${data.post_id}"]`);
    if (postElement) {
        const likeButton = postElement.querySelector('.like-button');
        likeButton.innerHTML = `♥ ${data.likes}`;
        
        if (data.user_id === parseInt(document.getElementById('username').dataset.userId)) {
            if (data.action === 'liked') {
                likeButton.classList.add('liked');
            } else {
                likeButton.classList.remove('liked');
            }
        }
    }
}