import rospy
from   yaw_controller import YawController
from   pid            import PID
from   lowpass        import LowPassFilter
from   std_msgs.msg   import Float32


GAS_DENSITY = 2.858
ONE_MPH = 0.44704

class Controller(object):

    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit, accel_limit,
                 wheel_radius, wheel_base, steer_ratio, max_lat_accel, max_steer_angle):
        self.vehicle_mass = vehicle_mass + fuel_capacity * GAS_DENSITY
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.wheel_radius = wheel_radius
        self.wheel_base = wheel_base
        self.steer_ratio = steer_ratio
        self.max_lat_accel = max_lat_accel
        self.max_steer_angle = max_steer_angle

        self.max_brake_torque = self.vehicle_mass * abs(self.decel_limit) * self.wheel_radius

        self.last_time    = None

        self.pid_control  = PID(0.4, 0.1, 0.0, self.decel_limit, self.accel_limit)

        self.yaw_control  = YawController(wheel_base=self.wheel_base,
                                          steer_ratio=self.steer_ratio,
                                          min_speed=0.0,
                                          max_lat_accel=self.max_lat_accel,
                                          max_steer_angle=self.max_steer_angle)


    def control(self, twist_cmd, current_velocity, dbw_enabled):

        if not all((twist_cmd, current_velocity)):
            return 0.0, 0.0, 0.0

        desired_linear_velocity = twist_cmd.twist.linear.x
        desired_angular_velocity = twist_cmd.twist.angular.z

        current_linear_velocity  = current_velocity.twist.linear.x
        current_angular_velocity = current_velocity.twist.angular.z

        if abs(desired_linear_velocity) < 1.0:
            self.pid_control.reset()

        if self.last_time is None:
            self.last_time = rospy.get_time()
            return 0.0, 0.0, 0.0

        if dbw_enabled:
            time           = rospy.get_time()
            delta_t        = time - self.last_time
            self.last_time = time

            velocity_error = desired_linear_velocity - current_linear_velocity
            control        = self.pid_control.update(velocity_error, delta_t)

            throttle = 0.0
            brake = 0.0

            if control > 0:
                throttle = control
            else:
                brake = self.vehicle_mass * abs(control) * self.wheel_radius

            steering = self.yaw_control.get_steering(desired_linear_velocity,
                                                     desired_angular_velocity,
                                                     current_linear_velocity)

            return throttle, brake, steering

        else:
            self.pid_control.reset()
            return 0.0, 0.0, 0.0
