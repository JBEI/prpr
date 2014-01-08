module.exports = function(grunt) {
 
  grunt.registerTask('watch', [ 'watch' ]);
 
  grunt.initConfig({
    less: {
      style: {
        files: {
          "static/css/diva.css": "less/diva.less",
          "static/css/responsive.css": "less/responsive.less",
        }
      }
    },
    jade: {
        compile: {
            options: {
                data: {
                    debug: false
                }
            },
            files: {
                'pages/page.html': 'jade/page.jade',
                'pages/page_dev.html': 'jade/page_dev.jade',
                'pages/dev.html': 'jade/dev.jade',
                'pages/dev-mf.html': 'jade/dev-mf.jade',
                'pages/copyright.html': 'jade/copyright.jade',
                'pages/disclaimer.html': 'jade/disclaimer.jade'
            }
        }
    },
    watch: {
      css: {
        files: ['less/*.less'],
        tasks: ['less:style'],
        options: {
          livereload: true,
        }
      },
      jade: {
          files: ['jade/*.jade'],
          tasks: ['jade']
      }
    }
  });
 
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-jade');
  grunt.loadNpmTasks('grunt-contrib-watch');
 
};
