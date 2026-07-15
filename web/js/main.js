/**
 * main.js - 主交互逻辑
 * 导航、主题切换、滚动动画
 */

(function() {
    'use strict';

    // ========================================
    // Theme Toggle - 主题切换
    // ========================================
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    const lightIcon = themeToggle.querySelector('.theme-icon-light');
    const darkIcon = themeToggle.querySelector('.theme-icon-dark');

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (theme === 'dark') {
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'inline';
        } else {
            lightIcon.style.display = 'inline';
            darkIcon.style.display = 'none';
        }
    }

    // Load saved theme or respect system preference
    var savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        setTheme('dark');
    }

    themeToggle.addEventListener('click', function() {
        var current = html.getAttribute('data-theme');
        setTheme(current === 'dark' ? 'light' : 'dark');
    });

    // ========================================
    // Navigation - 导航
    // ========================================
    var navLinks = document.getElementById('navLinks');
    var navHamburger = document.getElementById('navHamburger');
    var navLinksItems = navLinks.querySelectorAll('a');

    // Hamburger menu toggle
    navHamburger.addEventListener('click', function() {
        navLinks.classList.toggle('open');
    });

    // Close mobile menu on link click
    navLinksItems.forEach(function(link) {
        link.addEventListener('click', function() {
            navLinks.classList.remove('open');
        });
    });

    // Active section highlighting
    var sections = document.querySelectorAll('.section, .hero');
    var navObserverOptions = {
        root: null,
        rootMargin: '-50% 0px -50% 0px',
        threshold: 0
    };

    var navObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                var id = entry.target.getAttribute('id');
                navLinksItems.forEach(function(link) {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === '#' + id) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, navObserverOptions);

    sections.forEach(function(section) {
        navObserver.observe(section);
    });

    // ========================================
    // Scroll Animations - 滚动动画
    // ========================================
    var fadeElements = document.querySelectorAll('.fade-in');

    var fadeObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                fadeObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    fadeElements.forEach(function(el) {
        fadeObserver.observe(el);
    });

    // ========================================
    // Footer Date - 页脚日期
    // ========================================
    var footerDate = document.getElementById('footerDate');
    if (footerDate) {
        var now = new Date();
        footerDate.textContent = now.getFullYear() + '年' + (now.getMonth() + 1) + '月';
    }

    // ========================================
    // Nav background on scroll
    // ========================================
    var nav = document.getElementById('nav');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            nav.style.boxShadow = '0 1px 10px ' + 'rgba(0,0,0,0.08)';
        } else {
            nav.style.boxShadow = 'none';
        }
    });

})();
