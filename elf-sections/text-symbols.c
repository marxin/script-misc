extern int __text_unlikely_start;
extern int __text_unlikely_end;
extern int __text_exit_start;
extern int __text_exit_end;
extern int __text_startup_start;
extern int __text_startup_end;
extern int __text_hot_start;
extern int __text_hot_end;
extern int __text_sorted_start;
extern int __text_sorted_end;
extern int __text_normal_start;
extern int __text_normal_end;
extern int __text_warning_start;
extern int __text_warning_end;

int __use_my(void) {
  return __text_unlikely_start + __text_unlikely_end + __text_exit_start +
         __text_exit_end + __text_startup_start + __text_startup_end +
         __text_hot_start + __text_hot_end + __text_sorted_start +
         __text_sorted_end + __text_normal_start + __text_normal_end +
         __text_warning_start + __text_warning_end;
}
