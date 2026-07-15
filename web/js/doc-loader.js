/**
 * doc-loader.js - 文档目录树渲染与iframe加载
 */

(function() {
    'use strict';

    var sidebar = document.getElementById('docSidebar');
    var featuredGrid = document.getElementById('docFeaturedGrid');
    var viewerHeader = document.getElementById('docViewerHeader');
    var viewerTitle = document.getElementById('docViewerTitle');
    var viewerFormat = document.getElementById('docViewerFormat');
    var viewerBody = document.getElementById('docViewerBody');
    var activeFileEl = null;

    // Format icons
    var FORMAT_ICONS = {
        md: '📝',
        pdf: '📕',
        docx: '📘',
        doc: '📘',
        txt: '📄',
        xlsx: '📊',
        xls: '📊',
        default: '📄'
    };

    function getFormatIcon(format) {
        return FORMAT_ICONS[format] || FORMAT_ICONS.default;
    }

    function getFormatLabel(format) {
        var labels = {
            md: 'Markdown',
            pdf: 'PDF',
            docx: 'Word',
            doc: 'Word',
            txt: 'Text',
            xlsx: 'Excel',
            xls: 'Excel'
        };
        return labels[format] || format.toUpperCase();
    }

    // ========================================
    // Render Featured Documents
    // ========================================
    function renderFeatured() {
        if (typeof DOC_CATALOG === 'undefined' || !featuredGrid) return;

        var featured = [];
        DOC_CATALOG.forEach(function(cat) {
            // Top-level featured docs
            (cat.documents || []).forEach(function(doc) {
                if (doc.featured) featured.push(doc);
            });
            // Sub-category featured docs
            (cat.subCategories || []).forEach(function(sub) {
                (sub.documents || []).forEach(function(doc) {
                    if (doc.featured) featured.push(doc);
                });
            });
        });

        if (featured.length === 0) {
            featuredGrid.innerHTML = '<p style="color:var(--color-text-tertiary);font-size:var(--font-size-sm)">运行构建脚本后显示精选文档</p>';
            return;
        }

        featuredGrid.innerHTML = '';
        featured.forEach(function(doc) {
            var card = document.createElement('div');
            card.className = 'doc-featured-card';
            card.innerHTML =
                '<div class="doc-featured-card-title">' + escapeHtml(doc.title) + '</div>' +
                '<div class="doc-featured-card-desc">' + escapeHtml(doc.summary || '') + '</div>' +
                '<div class="doc-featured-card-meta">' + getFormatIcon(doc.format) + ' ' + getFormatLabel(doc.format) + '</div>';
            card.addEventListener('click', function() {
                openDocument(doc);
            });
            featuredGrid.appendChild(card);
        });
    }

    // ========================================
    // Render Document Tree
    // ========================================
    function renderTree() {
        if (typeof DOC_CATALOG === 'undefined' || !sidebar) {
            if (sidebar) sidebar.innerHTML = '<p style="color:var(--color-text-tertiary);font-size:var(--font-size-sm);padding:1rem">运行构建脚本后显示文档目录</p>';
            return;
        }

        sidebar.innerHTML = '';

        DOC_CATALOG.forEach(function(category) {
            var catItem = document.createElement('div');
            catItem.className = 'doc-tree-item';

            // Category folder
            var folder = document.createElement('div');
            folder.className = 'doc-tree-folder';
            folder.innerHTML =
                '<span class="arrow">▶</span>' +
                '<span class="folder-icon">📁</span>' +
                '<span>' + escapeHtml(category.label || category.category) + '</span>';
            catItem.appendChild(folder);

            // Children container
            var children = document.createElement('div');
            children.className = 'doc-tree-children';

            // Direct documents
            (category.documents || []).forEach(function(doc) {
                children.appendChild(createFileItem(doc));
            });

            // Sub-categories
            (category.subCategories || []).forEach(function(sub) {
                var subFolder = document.createElement('div');
                subFolder.className = 'doc-tree-item';

                var subFolderEl = document.createElement('div');
                subFolderEl.className = 'doc-tree-folder';
                subFolderEl.innerHTML =
                    '<span class="arrow">▶</span>' +
                    '<span class="folder-icon">📂</span>' +
                    '<span>' + escapeHtml(sub.label || sub.name || '') + '</span>';
                subFolder.appendChild(subFolderEl);

                var subChildren = document.createElement('div');
                subChildren.className = 'doc-tree-children';

                (sub.documents || []).forEach(function(doc) {
                    subChildren.appendChild(createFileItem(doc));
                });

                subFolder.appendChild(subChildren);
                children.appendChild(subFolder);

                // Sub-folder toggle
                subFolderEl.addEventListener('click', function(e) {
                    e.stopPropagation();
                    subFolderEl.classList.toggle('open');
                    subChildren.classList.toggle('open');
                });
            });

            catItem.appendChild(children);
            sidebar.appendChild(catItem);

            // Category folder toggle
            folder.addEventListener('click', function() {
                folder.classList.toggle('open');
                children.classList.toggle('open');
            });
        });
    }

    function createFileItem(doc) {
        var fileItem = document.createElement('div');
        fileItem.className = 'doc-tree-file';
        fileItem.setAttribute('data-file', doc.file || '');
        fileItem.innerHTML =
            '<span class="file-icon">' + getFormatIcon(doc.format) + '</span>' +
            '<span>' + escapeHtml(doc.title) + '</span>';

        fileItem.addEventListener('click', function(e) {
            e.stopPropagation();
            openDocument(doc);

            // Highlight active
            if (activeFileEl) activeFileEl.classList.remove('active');
            fileItem.classList.add('active');
            activeFileEl = fileItem;
        });

        return fileItem;
    }

    // ========================================
    // Open Document in Viewer
    // ========================================
    function openDocument(doc) {
        viewerHeader.style.display = 'flex';
        viewerTitle.textContent = doc.title;
        viewerFormat.textContent = getFormatLabel(doc.format);

        if (doc.format === 'md' && doc.file) {
            // Load HTML file in iframe
            viewerBody.innerHTML =
                '<iframe src="' + doc.file + '" title="' + escapeHtml(doc.title) + '"></iframe>';
        } else if (doc.format === 'pdf' || doc.format === 'docx' || doc.format === 'doc' ||
                   doc.format === 'xlsx' || doc.format === 'xls') {
            // External file - cannot render inline
            viewerBody.innerHTML =
                '<div class="doc-viewer-external">' +
                '  <div class="doc-viewer-external-icon">' + getFormatIcon(doc.format) + '</div>' +
                '  <div class="doc-viewer-external-info">此文档为 ' + getFormatLabel(doc.format) + ' 格式，无法在网页内直接预览</div>' +
                (doc.originalPath ?
                    '  <div class="doc-viewer-external-path">' + escapeHtml(doc.originalPath) + '</div>' :
                    '') +
                '</div>';
        } else {
            // Try loading in iframe anyway
            if (doc.file) {
                viewerBody.innerHTML =
                    '<iframe src="' + doc.file + '" title="' + escapeHtml(doc.title) + '"></iframe>';
            } else {
                viewerBody.innerHTML =
                    '<div class="doc-viewer-placeholder">' +
                    '  <div class="doc-viewer-placeholder-icon">📂</div>' +
                    '  <p class="doc-viewer-placeholder-text">文档暂不可用</p>' +
                    '</div>';
            }
        }
    }

    // ========================================
    // Utilities
    // ========================================
    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ========================================
    // Initialize
    // ========================================
    renderFeatured();
    renderTree();

})();
